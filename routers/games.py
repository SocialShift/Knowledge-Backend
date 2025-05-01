from fastapi import APIRouter
from db.models import get_db
from sqlalchemy.orm import Session
from utils.file_handler import save_image, delete_file

router= APIRouter(prefix="/api/game")

