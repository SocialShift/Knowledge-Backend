from fastapi import Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from db.models import User, Profile, get_db
from typing import Optional
from datetime import date, datetime, timedelta

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
    
    # Update login streak - only check once per day
    last_streak_check = request.session.get("last_streak_check")
    today = date.today().isoformat()
    
    if last_streak_check != today:
        # Update the session to mark that we've checked the streak today
        request.session["last_streak_check"] = today
        
        # Get the user's profile
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        if profile:
            today_date = date.today()
            
            # Check if this is the first login ever
            if profile.last_login_date is None:
                profile.current_login_streak = 1
                profile.max_login_streak = 1
            else:
                # Calculate days since last login
                days_since_last_login = (today_date - profile.last_login_date).days
                
                # If it's a new day (not today) and they logged in yesterday, increment streak
                if days_since_last_login == 1:
                    profile.current_login_streak += 1
                    # Update max streak if current streak is higher
                    if profile.current_login_streak > profile.max_login_streak:
                        profile.max_login_streak = profile.current_login_streak
                # If they missed a day or more, reset streak to 1
                elif days_since_last_login > 1:
                    profile.current_login_streak = 1
            
            # Update last login date to today
            profile.last_login_date = today_date
            
            # Add bonus points for login streaks
            streak_bonus = 0
            # Bonus for 7-day streak
            if profile.current_login_streak == 7:
                streak_bonus += 50
            # Bonus for 30-day streak
            elif profile.current_login_streak == 30:
                streak_bonus += 200
            # Daily login bonus (always give this when we update the streak)
            streak_bonus += 5
            
            # Apply streak bonus
            if streak_bonus > 0:
                profile.points += streak_bonus
                
                # Store the bonus in the session so we can display it to the user
                request.session["streak_bonus"] = streak_bonus
                request.session["current_streak"] = profile.current_login_streak
            # Save changes
            db.commit()
    return user

def create_session(request: Request, user: User):
    request.session["user_id"] = user.id
    request.session["email"] = user.email

def end_session(request: Request):
    request.session.clear()

def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin or current_user.email != "a@a.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user