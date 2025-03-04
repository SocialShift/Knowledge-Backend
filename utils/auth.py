from fastapi import Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from db.models import User, get_db
from typing import Optional

SECRET_KEY=  "enter-your-secret-key"

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
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account de-activated"
        )   
    
    return user

def create_session(request: Request, user: User):
    request.session["user_id"] = user.id
    request.session["email"] = user.email

def end_session(request: Request):
    request.session.clear()

def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user