from fastapi import Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from db.models import User, get_db
from typing import Optional


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

def create_session(request: Request, user: User):
    request.session["user_id"] = user.id
    request.session["username"] = user.username

def end_session(request: Request):
    request.session.clear()