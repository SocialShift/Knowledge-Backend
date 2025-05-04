from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from enum import IntEnum

class GameTypes(IntEnum):
    GUESS_THE_YEAR = 1
    IMAGE_GUESS = 2
    FILL_IN_THE_BLANK = 3

# Base schemas
class GameOptionBase(BaseModel):
    text: str
    is_correct: bool

class GameQuestionBase(BaseModel):
    title: str
    game_type: GameTypes
    image_url: Optional[str] = None

# Create schemas - Used for validation only, not for direct API input
class GameOptionCreate(GameOptionBase):
    pass

# Response schemas
class GameOption(GameOptionBase):
    id: int
    question_id: int

    class Config:
        orm_mode = True

class GameQuestion(GameQuestionBase):
    id: int
    created_at: datetime
    options: List[GameOption]

    class Config:
        orm_mode = True

# Game Attempt schemas
class GameAttemptCreate(BaseModel):
    standalone_question_id: int
    selected_option_id: int

class GameAttempt(BaseModel):
    id: int
    user_id: int
    game_id: int
    selected_option_id: Optional[int]
    is_correct: bool
    created_at: datetime

    class Config:
        orm_mode = True

class PaginatedGames(BaseModel):
    total: int
    items: List[GameQuestion]
    page: int
    size: int
    pages: int