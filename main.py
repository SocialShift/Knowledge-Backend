from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from routers import users, contacts, organizations, products
from db.models import engine, Base
app= FastAPI()


Base.metadata.create_all(bind=engine)

app.include_router(users.router)


if __name__== "__main__":
    import uvicorn
    uvicorn.run(app, port=7000, reload=True)