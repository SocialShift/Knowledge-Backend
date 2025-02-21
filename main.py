from fastapi import FastAPI
from routers import users, stories_timelines
from db.models import engine, Base
from utils.auth import SECRET_KEY

app= FastAPI()

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
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



Base.metadata.create_all(bind=engine)

app.include_router(users.router)
app.include_router(stories_timelines.router)


if __name__== "__main__":
    import uvicorn
    uvicorn.run(app)