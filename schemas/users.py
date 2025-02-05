from pydantic import BaseModel,Field,EmailStr
from datetime import datetime

class LoginModel(BaseModel):
    email: EmailStr 
    password: str

class UserCreateModel(BaseModel):
    email: EmailStr 
    password: str
    confirm_password: str= Field(exclude=True)


class UserModel(BaseModel):
    email: EmailStr  # Ensuring valid email format

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    joined_at: datetime
    is_active: bool

    class Config:
        orm_mode = True 

class ProfileUpdate(BaseModel):
    user: UserModel= None
    nickname: str= None
    avatar_url:str= None
    language_preference: str= None
    pronouns: str= None
    location: str= None
    learning_style: dict= None
    accessibility_settings: dict= None

#class UserModel