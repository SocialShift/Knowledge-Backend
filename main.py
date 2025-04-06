from fastapi import FastAPI
from routers import users, stories_timelines
from db.models import engine, Base
from utils.auth import SECRET_KEY
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app= FastAPI()


app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session_cookie",
    max_age=1800000000000  # 30 minutes in seconds
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the media directory to serve static files
media_path = Path("media")
media_path.mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")

Base.metadata.create_all(bind=engine)

app.include_router(users.router)
app.include_router(stories_timelines.router)

# Include admin
from sqladmin import Admin
admin = Admin(app, engine)

# Register admin views
from db.admin import (
    UserAdmin, 
    ProfileAdmin, 
    TimelineAdmin, 
    StoryAdmin, 
    QuizAdmin,
    QuestionAdmin,
    OptionAdmin,
    CharacterAdmin, 
    OnThisDayAdmin,
    QuizAttemptAdmin,
    UserStoryLikeAdmin,
    TimestampAdmin
)

admin.add_view(UserAdmin)
admin.add_view(ProfileAdmin)
admin.add_view(TimelineAdmin)
admin.add_view(StoryAdmin)
admin.add_view(QuizAdmin)
admin.add_view(QuestionAdmin)
admin.add_view(OptionAdmin)
admin.add_view(CharacterAdmin)
admin.add_view(OnThisDayAdmin)
admin.add_view(QuizAttemptAdmin)
admin.add_view(UserStoryLikeAdmin)
admin.add_view(TimestampAdmin)

if __name__== "__main__":
    import uvicorn
    uvicorn.run(app)