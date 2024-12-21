import csv
import os
from pathlib import Path
from typing import List

from loguru import logger

from src.model import AnkiDeck, AnkiCard
from src.service.llm_service import LLMService
from src.service.persitence_service import PersistenceService


class DeckService:
    _WORDS_PROMPT = """You are a language education expert creating vocabulary-focused Anki flashcards. For each new word or phrase in the text, create comprehensive cards that ensure deep understanding and retention. Focus on:

1. Word Context:
   - How the word is used in real situations
   - Common collocations and phrases
   - Register (formal/informal usage)

2. Word Relationships:
   - Related words (synonyms, antonyms)
   - Word families (derivations, common prefixes/suffixes)
   - False friends 
   
3. Usage Patterns:
   - Example sentences showing different contexts
   - Common expressions containing the word
   - Grammar patterns associated with the word

4. Memory Aids:
   - Etymology when helpful
   - Memorable mnemonics
   - Connection to cognates or similar words
   - Breaking down compound words

5. Cultural Context:
   - Cultural associations
   - Regional variations in meaning
   - Idiomatic usage

For each word, create multiple cards types:
- Basic recall (translation to desired language)
- Usage in context (fill-in-the-blank sentences)
- Collocation practice
- Picture/situation association
- Word family relationships

Ensure cards include:
- Clear pronunciation notes
- Relevant parts of speech
- Common mistakes to avoid
- Usage level (beginner/intermediate/advanced)
"""

    _GRAMMAR_PROMPT = f"""You are a language education expert creating Anki flashcards. 
Create comprehensive cards that go beyond simple translations and help students deeply understand language concepts. 
Focus on:

1. Grammar patterns and their usage
2. Common phrases and their contextual meanings
3. Cultural notes and usage variations
4. Conjugation patterns and their applications
5. Word relationships and connections
6. Usage examples in different contexts

For each concept, create multiple cards that approach it from different angles. 
"""

    def __init__(
        self,
        llm_service: LLMService,
        persistence_service: PersistenceService,
    ):
        self.persistence_service = persistence_service
        self.llm_service = llm_service

    def create_deck(
        self,
        book_name: str,
        start_page: int,
        end_page: int,
        out_dir: Path,
        system_prompt: str,
    ) -> str:
        """
        Create an Anki deck from specified pages of a textbook
        """
        logger.info(
            f"Starting deck creation from {book_name}, pages {start_page}-{end_page}"
        )
        all_cards = []

        for page_num in range(start_page, end_page + 1):
            logger.info(f"Processing page {page_num}")
            page = self.persistence_service.get_parsed_page(book_name, page_num)
            if not page:
                logger.info(f"No content for page {page_num}, skipping...")
                continue

            cards = self._generate_cards_for_page(page.content, page_num, system_prompt)
            all_cards.extend(cards)

        if not all_cards:
            raise ValueError("No cards generated for the specified pages")

        book_name = os.path.splitext(os.path.basename(book_name))[0]
        filename = f"deck_{book_name}_{start_page}-{end_page}.csv"
        output_file = out_dir / book_name / filename
        if not output_file.parent.exists():
            output_file.parent.mkdir(parents=True)

        self._save_to_csv(output_file, all_cards)
        logger.info(f"Deck created and saved to {filename}")
        return filename

    def default_create_deck(
        self, book_name: str, start_page: int, end_page: int, out_dir: Path
    ) -> str:
        """
        Create an Anki deck from specified pages of a textbook
        """
        logger.info(
            f"Starting deck creation from {book_name}, pages {start_page}-{end_page}"
        )
        all_cards = []

        for page_num in range(start_page, end_page + 1):
            logger.info(f"Processing page {page_num}")
            page = self.persistence_service.get_parsed_page(book_name, page_num)
            if not page:
                logger.info(f"No content for page {page_num}, skipping...")
                continue

            grammar_cards = self._generate_cards_for_page(
                page.content, page_num, self._GRAMMAR_PROMPT
            )
            words_cards = self._generate_cards_for_page(
                page.content, page_num, self._WORDS_PROMPT
            )
            all_cards.extend(grammar_cards)
            all_cards.extend(words_cards)

        if not all_cards:
            raise ValueError("No cards generated for the specified pages")

        book_name = os.path.splitext(os.path.basename(book_name))[0]
        filename = f"deck_{book_name}_{start_page}-{end_page}.csv"
        output_file = out_dir / book_name / filename
        if not output_file.parent.exists():
            output_file.parent.mkdir(parents=True)

        self._save_to_csv(output_file, all_cards)
        logger.info(f"Deck created and saved to {filename}")
        return filename

    def _generate_cards_for_page(
        self, content: str, page_num: int, system_prompt: str
    ) -> List[AnkiCard]:
        """Generate Anki cards for a single page using GPT-4"""
        logger.info(f"Generating cards for page {page_num}")

        user_prompt = f"""Create Anki cards for this textbook page content:

{content}

Focus on creating cards that:
- Break down complex grammar concepts into digestible pieces
- Include real-world usage examples
- Highlight cultural context when relevant
- Create connections between related concepts
- Include common mistakes to avoid

Page number for reference: {page_num}"""

        logger.info("Sending request to OpenAI for card generation...")

        try:
            logger.debug(f"LLM response received for page {page_num}")
            deck: AnkiDeck = self.llm_service.prompt_with_structure(
                system_prompt=system_prompt, prompt=user_prompt, response_model=AnkiDeck
            )
            cards = deck.cards
            logger.info(f"Generated {len(cards)} cards for page {page_num}")
            logger.debug(cards)
            return cards
        except Exception as e:
            logger.exception(f"Error processing page {page_num}: {e}")
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
