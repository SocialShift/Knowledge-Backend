from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import List

class LoginModel(BaseModel):
    email: EmailStr 
    password: str




class UserCreateModel(BaseModel):
    email: EmailStr 
    password: str
    confirm_password: str = Field(exclude=True)

class UserModel(BaseModel):
    email: EmailStr  # Ensuring valid email format

class UserResponse(BaseModel):  
    id: int
    email: EmailStr
    joined_at: datetime
    is_active: bool

    class Config:
        from_attributes = True 

class ProfileUpdate(BaseModel):
    nickname: str = None
    language_preference: str = None
    pronouns: str = None
    location: str = None
    personalization_questions: dict = None
    
    class Config:
        arbitrary_types_allowed = True




class UserEmailUpdate(BaseModel):
    email: EmailStr

class UserPasswordChange(BaseModel):
    current_password: str 
    new_password: str 
    confirm_new_password: str= Field(exclude=True)

class UserPasswordForgot(BaseModel):
    new_password: str 
    confirm_new_password: str



class LeaderboardEntryModel(BaseModel):
    rank: int
    user_id: int
    nickname: str
    avatar_url: str = None
    points: int
    current_streak: int
    max_streak: int

class LeaderboardResponseModel(BaseModel):
    leaderboard: List[LeaderboardEntryModel]
    user_rank: int = None