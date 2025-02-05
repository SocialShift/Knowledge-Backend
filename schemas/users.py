from pydantic import BaseModel,Field

class LoginModel(BaseModel):
    email: str 
    password: str

class UserCreateModel(BaseModel):
    email: str 
    password: str
    confirm_password: str= Field(exclude=True)

class ProfileUpdate(BaseModel):
    nickname: str= None
    avatar_url:str= None
    language_preference: str= None
    pronouns: str= None
    location: str= None
    learning_style: dict= None
    accessibility_settings: dict= None

#class UserModel