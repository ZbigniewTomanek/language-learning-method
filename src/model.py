from pydantic import BaseModel


class AnkiCard(BaseModel):
    front: str
    back: str


class AnkiDeck(BaseModel):
    cards: list[AnkiCard]


class ExtractedExercise(BaseModel):
    title: str
    instructions: str
    questions: list[str]


class ExtractedExercises(BaseModel):
    exercises: list[ExtractedExercise]
