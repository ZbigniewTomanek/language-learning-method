import csv
from pathlib import Path
from typing import List

from loguru import logger
from math import floor
from pydantic import BaseModel

from src.model import AnkiCard, AnkiDeck
from src.service.llm_service import LLMService


class Topic(BaseModel):
    name: str
    description: str
    difficulty_level: str  # beginner/intermediate/advanced


class ListOfTopics(BaseModel):
    topics: List[Topic]


class DeckFromPromptService:
    _TOPIC_EVALUATION_PROMPT = """You are a language education expert. Analyze the user's request for flashcards and break it down into distinct topics that should be covered.
    For each topic provide:
    1. Name - short descriptive name
    2. Description - detailed explanation of what should be covered
    3. Difficulty level (beginner/intermediate/advanced)

    Ensure topics are:
    - Distinct and non-overlapping
    - Specific enough to generate focused flashcards
    - Relevant to the user's request
    """

    _FLASHCARD_GENERATION_PROMPT = """Create comprehensive flashcards for the following topic in language learning:

    Topic: {topic_name}
    Description: {topic_description}
    Level: {difficulty_level}
    Number of cards to generate: {num_cards}

    Create cards that:
    - Break down complex concepts into digestible pieces
    - Include real-world usage examples
    - Highlight cultural context when relevant
    - Create connections between related concepts
    - Include common mistakes to avoid

    Each card should have:
    - Clear and concise front side
    - Comprehensive back side with examples and explanations
    """

    def __init__(
        self,
        llm_service: LLMService,
    ):
        self.llm_service = llm_service

    def create_deck(self, prompt: str, num_of_flashcards: int, out_dir: Path) -> str:
        logger.info(f"Starting deck creation for prompt: {prompt[:100]}...")

        topics = self._evaluate_prompt_into_topics(prompt)
        logger.info(f"Identified {len(topics.topics)} topics")

        # Calculate cards per topic (distribute evenly)
        cards_per_topic = floor(num_of_flashcards / len(topics.topics))
        remaining_cards = num_of_flashcards % len(topics.topics)

        all_cards = []

        # Generate cards for each topic
        for i, topic in enumerate(topics.topics):
            # Add an extra card to early topics if we have remaining cards
            topic_cards = cards_per_topic + (1 if i < remaining_cards else 0)

            cards = self._generate_cards_for_topic(topic, topic_cards)
            all_cards.extend(cards)
            logger.info(f"Generated {len(cards)} cards for topic: {topic.name}")

        if not all_cards:
            raise ValueError("No cards were generated")

        # Create filename based on first topic name and number of cards
        filename = f"deck_{topics.topics[0].name.lower().replace(' ', '_')}_{num_of_flashcards}.csv"
        output_file = out_dir / filename
        if not output_file.parent.exists():
            output_file.parent.mkdir(parents=True)

        self._save_to_csv(output_file, all_cards)
        logger.info(f"Deck created and saved to {filename}")
        return filename

    def _evaluate_prompt_into_topics(self, prompt: str) -> ListOfTopics:
        """Convert user prompt into structured topics"""
        logger.info("Evaluating prompt into topics...")

        try:
            topics: ListOfTopics = self.llm_service.prompt_with_structure(
                system_prompt=self._TOPIC_EVALUATION_PROMPT,
                prompt=prompt,
                response_model=ListOfTopics,
            )
            logger.info(f"Successfully identified {len(topics.topics)} topics")
            return topics
        except Exception as e:
            logger.exception(f"Error evaluating prompt into topics: {e}")
            raise

    def _generate_cards_for_topic(self, topic: Topic, num_cards: int) -> List[AnkiCard]:
        """Generate specified number of cards for a given topic"""
        logger.info(f"Generating {num_cards} cards for topic: {topic.name}")

        formatted_prompt = self._FLASHCARD_GENERATION_PROMPT.format(
            topic_name=topic.name,
            topic_description=topic.description,
            difficulty_level=topic.difficulty_level,
            num_cards=num_cards,
        )

        try:
            deck: AnkiDeck = self.llm_service.prompt_with_structure(
                system_prompt=formatted_prompt,
                prompt="Generate the flashcards as specified above.",
                response_model=AnkiDeck,
            )
            return deck.cards
        except Exception as e:
            logger.exception(f"Error generating cards for topic {topic.name}: {e}")
            return []

    @staticmethod
    def _save_to_csv(file: Path, cards: List[AnkiCard]) -> None:
        """Save generated cards to CSV file"""
        logger.info(f"Saving {len(cards)} cards to {file}")
        with open(file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["front", "back"])
            for card in cards:
                writer.writerow([card.front, card.back])
        logger.info(f"Cards successfully saved to {file}")
