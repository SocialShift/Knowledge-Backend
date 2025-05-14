from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime, date
from typing import Optional, List
from fastapi import UploadFile, File
from pydantic import field_validator
from db.models import StoryType, TimelineCategory

class OnThisDayCreateModel(BaseModel):
    date: date
    title: str
    short_desc: str
    image_file: Optional[UploadFile] = None
    story_id: Optional[int] = None  # Can be linked to a Story
    
    class Config:
        arbitrary_types_allowed = True

class OnThisDayResponseModel(BaseModel):
    id: int
    date: date
    title: str
    short_desc: str
    image_url: Optional[str] = None
    story_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True  

class TimelineCreateModel(BaseModel):
    title: str
    year_range: str
    overview: str
    main_character_id: Optional[int] = None
    categories: Optional[List[str]] = None

    @field_validator('title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v

    class Config:
        arbitrary_types_allowed = True

class TimelineUpdateModel(BaseModel):
    title: Optional[str] = None
    year_range: Optional[str] = None
    overview: Optional[str] = None
    main_character_id: Optional[int] = None
    categories: Optional[List[str]] = None  # List of category tags

class TimeStampCreateModel(BaseModel):
    time_sec: int = Field(..., gt=0, description="Timestamp in seconds")  # Must be greater than 0
    label: str = None  
    
class StoryCreateModel(BaseModel):
    title: str
    desc: str 
    timeline_id: int = None 
    story_date: date
    story_type: Optional[StoryType] = None
    timestamps: list[TimeStampCreateModel] = []

    class Config:
        arbitrary_types_allowed = True

class StoryUpdateModel(BaseModel):
    title: str = None
    desc: str = None
    timeline_id: int = None 
    story_date: date = None
    story_type: Optional[StoryType] = None
    timestamps: list[TimeStampCreateModel] = None

    class Config:
        arbitrary_types_allowed = True

class OptionCreateModel(BaseModel):
    text: str
    is_correct: bool

class OptionResponseModel(BaseModel):
    id: int
    text: str
    is_correct: bool
    
    class Config:
        from_attributes = True

class QuestionCreateModel(BaseModel):
    text: str
    options: list[OptionCreateModel]  # Must have 4 options
    """
    @field_validator('options')
    def validate_options(cls, v):
        if len(v) != 4:
            raise ValueError('Each question must have exactly 4 options')
        
        # Check that exactly one option is correct
        correct_options = sum(1 for option in v if option.is_correct)
        if correct_options != 1:
            raise ValueError('Each question must have exactly one correct option')
        
        return v
    """

class QuestionResponseModel(BaseModel):
    id: int
    text: str
    options: list[OptionResponseModel]
    
    class Config:
        from_attributes = True

class QuizCreateModel(BaseModel):
    story_id: int
    questions: list[QuestionCreateModel]  # Multiple questions per quiz
    
    @field_validator('questions')
    def validate_questions(cls, v):
        if len(v) < 1:
            raise ValueError('Quiz must have at least one question')
        return v

class QuizUpdateModel(BaseModel):
    questions: list[QuestionCreateModel] = None
    
    @field_validator('questions')
    def validate_questions(cls, v):
        if v is not None and len(v) < 1:
            raise ValueError('Quiz must have at least one question')
        return v

class QuizResponseModel(BaseModel):
    id: int
    story_id: int
    created_at: datetime
    questions: list[QuestionResponseModel]
    
    class Config:
        from_attributes = True

# New schema for quiz submissions
class QuizAnswerModel(BaseModel):
    question_id: int
    selected_option_id: int

class QuizSubmissionModel(BaseModel):
    quiz_id: int
    answers: list[QuizAnswerModel]

class QuizAttemptResponseModel(BaseModel):
    id: int
    quiz_id: int
    completed: bool
    score: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class CharacterCreateModel(BaseModel):
    name: str
    persona: str
    avatar_file: Optional[UploadFile] = None
    
    class Config:
        arbitrary_types_allowed = True

class CharacterUpdateModel(BaseModel):
    name: Optional[str] = None
    persona: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True

class CharacterResponseModel(BaseModel):
    id: int
    name: str
    persona: str
    avatar_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True