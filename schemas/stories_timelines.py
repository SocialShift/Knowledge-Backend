from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime,date

from typing import Optional

class OnThisDayCreateModel(BaseModel):
    date: date
    title: str
    short_desc: str
    image_url: str = None
    story_id: Optional[int] = None  # Can be linked to a Story

class OnThisDayResponseModel(OnThisDayCreateModel):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  

class TimelineCreateModel(BaseModel):
    title: str
    thumbnail_url: str
    year_range: str
    overview: str

class TimelineUpdateModel(BaseModel):
    title: str= None
    thumbnail_url: str= None
    year_range: str= None
    overview: str= None

class TimeStampCreateModel(BaseModel):
    time_sec: int = Field(..., gt=0, description="Timestamp in seconds")  # Must be greater than 0
    label: str = None  
    

class StoryCreateModel(BaseModel):
    title: str
    desc: str 
    thumbnail_url: str 
    video_url: str 
    timeline_id: int= None 
    timestamps: list[TimeStampCreateModel] = []


class StoryUpdateModel(BaseModel):
    title: str= None
    desc: str= None
    thumbnail_url: str = None
    video_url: str = None
    timeline_id: int= None 
    timestamps: list[TimeStampCreateModel] = []