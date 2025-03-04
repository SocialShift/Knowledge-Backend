from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime, date
from typing import Optional
from fastapi import UploadFile, File
from pydantic import field_validator

class OnThisDayCreateModel(BaseModel):
    date: date
    title: str
    short_desc: str
    image_file: UploadFile = None
    story_id: int = None  # Can be linked to a Story

class OnThisDayResponseModel(BaseModel):
    id: int
    date: date
    title: str
    short_desc: str
    image_url: str = None
    story_id: int = None
    created_at: datetime

    class Config:
        from_attributes = True  

class TimelineCreateModel(BaseModel):
    title: str
    year_range: str
    overview: str

    @field_validator('title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v

    class Config:
        arbitrary_types_allowed = True

class TimelineUpdateModel(BaseModel):
    title: str = None
    year_range: str = None
    overview: str = None

class TimeStampCreateModel(BaseModel):
    time_sec: int = Field(..., gt=0, description="Timestamp in seconds")  # Must be greater than 0
    label: str = None  
    
class StoryCreateModel(BaseModel):
    title: str
    desc: str 
    timeline_id: int = None 
    timestamps: list[TimeStampCreateModel] = []

    class Config:
        arbitrary_types_allowed = True

class StoryUpdateModel(BaseModel):
    title: str = None
    desc: str = None
    timeline_id: int = None 
    timestamps: list[TimeStampCreateModel] = None

    class Config:
        arbitrary_types_allowed = True

class OptionCreateModel(BaseModel):
    text: str
    is_correct: bool

class QuestionCreateModel(BaseModel):
    text: str
    options: list[OptionCreateModel]  # Must have 4 options

class QuizCreateModel(BaseModel):
    story_id: int
    questions: list[QuestionCreateModel]  # Multiple questions per quiz