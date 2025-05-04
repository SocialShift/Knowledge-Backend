from fastapi import FastAPI
from routers import users, stories_timelines, communities_posts, games
from db.models import engine, Base
from utils.auth import SECRET_KEY
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import sqladmin
import shutil
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

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

#app.add_middleware(HTTPSRedirectMiddleware)


static_path = Path("static")
static_path.mkdir(exist_ok=True)

# Path to sqladmin's statics directory
sqladmin_static_path = os.path.join(os.path.dirname(sqladmin.__file__), "statics")

# Copy files from sqladmin/statics to your static/ dir
for item in os.listdir(sqladmin_static_path):
    src = os.path.join(sqladmin_static_path, item)
    dest = os.path.join(static_path, item)
    if os.path.isdir(src):
        shutil.copytree(src, dest, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dest)

# Mount your static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

media_path = Path("media")
media_path.mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")

Base.metadata.create_all(bind=engine)

app.include_router(users.router)
app.include_router(stories_timelines.router)
app.include_router(communities_posts.router)
app.include_router(games.router)

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
    TimestampAdmin,
    FeedbackAdmin,
    StandAloneGameQuestionAdmin,
    StandAloneGameOptionAdmin
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
admin.add_view(FeedbackAdmin)
admin.add_view(StandAloneGameQuestionAdmin)
admin.add_view(StandAloneGameOptionAdmin)

if __name__== "__main__":
    import uvicorn
    uvicorn.run(app)