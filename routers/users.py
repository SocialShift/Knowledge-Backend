from fastapi import APIRouter, Depends, Request, HTTPException, status, UploadFile, File, Form
from db.models import get_db, User, Profile, QuizAttempt, UserFollow, VerificationOTP
from sqlalchemy.orm import Session
from schemas.users import (
    UserCreateModel, 
    LoginModel, 
    ProfileUpdate, 
    UserEmailUpdate, 
    UserPasswordChange, 
    FollowRequest, 
    FollowerResponse,
    EmailVerificationRequest,
    ResendVerificationRequest
)
from fastapi.responses import JSONResponse
from db.models import pwd_context, Feedback
from utils.auth import get_current_user, create_session, end_session
from utils.file_handler import save_image, delete_file
from utils.email_sender import generate_otp, send_verification_email
import json
from datetime import datetime, date, timedelta
from sqlalchemy import desc
from schemas.users import FeedbackCreateModel

router = APIRouter(prefix="/api/auth")

@router.post('/create-user')
async def create_user(request: Request, data: UserCreateModel, db: Session = Depends(get_db)):
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )


    elif db.query(User).filter(User.email == data.email).first():
        return JSONResponse(
            {"detail":"Email already exists"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    elif len(data.password) < 8:
        return JSONResponse(
            {"detail": "Password must be at least 8 characters long"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    # Your success logic here
    new_user= User(
        email= data.email
    )
    new_user.set_password(data.password)
    print(new_user)
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
        # Generate username after user is created and has an ID
        new_user.generate_username()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    new_profile= Profile(user_id= new_user.id)
    db.add(new_profile)
    try:
        db.commit()
        db.refresh(new_profile)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    # Generate and send verification email
    await send_verification_otp(new_user.email, db)
    # Create session for the new user
    create_session(request, new_user)
    
    return JSONResponse({
        'detail': 'User created. Please check your email for verification code.',
        'user': {
            'id': new_user.id,
            'email': new_user.email,
            'username': new_user.username,
            'is_verified': new_user.is_verified
        }
    }, status_code=status.HTTP_201_CREATED)

async def send_verification_otp(email: str, db: Session):
    """Generate and send a verification OTP to the user's email"""
    
    # Generate a 6-digit OTP
    otp = generate_otp(6)
    
    # Set expiration time (10 minutes from now)
    expires_at = datetime.now() + timedelta(minutes=10)
    
    # Create OTP record in database
    verification_otp = VerificationOTP(
        email=email,
        otp=otp,
        expires_at=expires_at
    )
    
    # Save to database
    db.add(verification_otp)
    try:
        db.commit()
        # Send email with OTP
        send_verification_email(email, otp)
    except Exception as e:
        db.rollback()
        print(f"Error sending verification email: {e}")

@router.post('/verify-email')
async def verify_email(data: EmailVerificationRequest, db: Session = Depends(get_db)):
    """Verify user's email using the provided OTP"""
    
    # Find the latest OTP for this email that hasn't been used
    verification = db.query(VerificationOTP).filter(
        VerificationOTP.email == data.email,
        VerificationOTP.is_used == False
    ).order_by(desc(VerificationOTP.created_at)).first()
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No verification code found for this email"
        )
    
    if not verification.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one."
        )
    
    if verification.otp != data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Mark OTP as used
    verification.mark_as_used()
    
    # Update user's verification status
    user = db.query(User).filter(User.email == data.email).first()
    if user:
        user.is_verified = True
    
    try:
        db.commit()
        return {"message": "Email verified successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete('/delete-user')
async def delete_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    my_user = db.query(User).filter(User.id == current_user.id).first()
    if not my_user:
        return HTTPException(detail="User not found, Unexpected error", status_code=status.HTTP_404_NOT_FOUND)
    db.delete(my_user)
    db.commit()
    return JSONResponse({'detail': "User deleted"}, status_code=status.HTTP_204_NO_CONTENT)

@router.post("/login")
async def login(request: Request, data: LoginModel, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user or not user.verify_password(data.password):
        return JSONResponse(
            {'detail': "Invalid or password is invalid"},
            status_code= status.HTTP_401_UNAUTHORIZED
            )
    
    # Create session
    create_session(request, user)
    
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    return {
        "user": {
            "id": user.id,
            "email": user.email
        },
        "streak": {
            "current": profile.current_login_streak if profile else 1,
            "max": profile.max_login_streak if profile else 1
        },
        "message": "Login successful"
    }

@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    end_session(request)
    return {"message": "Logged out successfully"}

@router.patch("/profile/update")
async def update_profile(
    nickname: str = Form(None),
    language_preference: str = Form(None),
    pronouns: str = Form(None),
    location: str = Form(None),
    personalization_questions: str = Form(None),
    avatar_file: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Create update data dictionary
    update_data = {}
    if nickname is not None:
        update_data["nickname"] = nickname
    if language_preference is not None:
        update_data["language_preference"] = language_preference
    if pronouns is not None:
        update_data["pronouns"] = pronouns
    if location is not None:
        update_data["location"] = location
    
    # Parse personalization questions if provided
    if personalization_questions is not None:
        try:
            update_data["personalization_questions"] = json.loads(personalization_questions)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid personalization questions JSON format")
    
    # Validate with Pydantic if there's data to update
    if update_data:
        try:
            validated_data = ProfileUpdate(**update_data)
            update_data = {k: v for k, v in validated_data.dict().items() if v is not None}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    # Handle avatar update
    old_avatar = None
    if avatar_file:
        old_avatar = profile.avatar_url
        update_data["avatar_url"] = await save_image(avatar_file)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    # Update the profile
    db.query(Profile).filter(Profile.user_id == current_user.id).update(update_data)
    
    try:
        db.commit()
        db.refresh(profile)
        
        # Delete old avatar if it was replaced
        if old_avatar and avatar_file:
            delete_file(old_avatar)
            
        return profile
    except Exception as e:
        db.rollback()
        # Delete the new avatar if there was an error
        if avatar_file and "avatar_url" in update_data:
            delete_file(update_data["avatar_url"])
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/profile/update/user-email")
async def update_user_profile(
    data: UserEmailUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    my_user = db.query(User).filter(User.id == current_user.id).first()

    if not my_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    # Update the email
    my_user.email = data.email

    db.commit()
    db.refresh(my_user)

    return {"message": "Email updated successfully", "email": my_user.email}

@router.post('/change-password')
async def change_password(
    data: UserPasswordChange, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Fetch the user instance
    my_user = db.query(User).filter(User.id == current_user.id).first()

    if not my_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User Not Found"
        )
    
    # Verify current password
    if not pwd_context.verify(data.current_password, my_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )

    # Check if new passwords match
    if data.new_password != data.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and Confirm Password didn't match"
        )

    # Hash new password and update user
    my_user.password = pwd_context.hash(data.new_password)
    
    db.commit()
    db.refresh(my_user)

    return {"message": "Password changed successfully."}

@router.get("/user/me")
async def get_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current user's profile with detailed information"""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Calculate user rank
    higher_ranked_count = db.query(Profile).filter(Profile.points > profile.points).count()
    user_rank = higher_ranked_count + 1
    
    # Get total number of users for percentile calculation
    total_users = db.query(Profile).count()
    percentile = round((1 - (user_rank / total_users)) * 100) if total_users > 0 else 0
    
    # Get completed quizzes count
    completed_quizzes = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.completed == True
    ).count()
    
    # Calculate days until next streak milestone
    next_milestone = 7 if profile.current_login_streak < 7 else 30
    days_to_milestone = next_milestone - (profile.current_login_streak % next_milestone)
    
    # Get streak bonus information from the session
    streak_bonus = request.session.get("streak_bonus", 0)
    
    # Clear the streak bonus from the session after reading it
    if streak_bonus:
        request.session.pop("streak_bonus", None)
    
    # Get followers and following counts
    followers_count = db.query(UserFollow).filter(UserFollow.followed_id == profile.id).count()
    following_count = db.query(UserFollow).filter(UserFollow.follower_id == profile.id).count()
    
    # Get followers and following (limited to 5 most recent)
    recent_followers = db.query(UserFollow).filter(UserFollow.followed_id == profile.id).order_by(desc(UserFollow.created_at)).limit(5).all()
    recent_following = db.query(UserFollow).filter(UserFollow.follower_id == profile.id).order_by(desc(UserFollow.created_at)).limit(5).all()
    
    # Check if current user is following this profile
    is_following = False
    if current_user.id != id:  # Don't check if viewing own profile
        current_user_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
        if current_user_profile:
            is_following = db.query(UserFollow).filter(
                UserFollow.follower_id == current_user_profile.id,
                UserFollow.followed_id == profile.id
            ).first() is not None
    
    # Format followers and following data
    followers_data = []
    for follow in recent_followers:
        follower_profile = follow.follower
        followers_data.append({
            "id": follower_profile.id,
            "nickname": follower_profile.nickname,
            "avatar_url": follower_profile.avatar_url,
            "user_id": follower_profile.user_id,
            "follow_date": follow.created_at
        })
    
    following_data = []
    for follow in recent_following:
        followed_profile = follow.followed
        following_data.append({
            "id": followed_profile.id,
            "nickname": followed_profile.nickname,
            "avatar_url": followed_profile.avatar_url,
            "user_id": followed_profile.user_id,
            "follow_date": follow.created_at
        })
    
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "is_verified": current_user.is_verified,
            "is_admin": current_user.is_admin,
            "joined_at": current_user.joined_at
        },
        "profile": {
            "id": profile.id,
            "badges": profile.badges,
            "nickname": profile.nickname,
            "avatar_url": profile.avatar_url,
            "points": profile.points,
            "referral_code": profile.referral_code,
            "total_referrals": profile.total_referrals,
            "language_preference": profile.language_preference,
            "pronouns": profile.pronouns,
            "location": profile.location,
            "personalization_questions": profile.personalization_questions,
            "followers": {
                "count": followers_count,
                "recent": followers_data
            },
            "following": {
                "count": following_count,
                "recent": following_data
            },
            "is_following": is_following
        },
        "stats": {
            "rank": user_rank,
            "total_users": total_users,
            "percentile": percentile,
            "completed_quizzes": completed_quizzes,
            "current_login_streak": profile.current_login_streak,
            "max_login_streak": profile.max_login_streak,
            "days_to_next_milestone": days_to_milestone,
            "next_milestone": next_milestone,
            "streak_bonus": streak_bonus
        }
    }


@router.get("/user/{id}")
async def get_profile(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current user's profile with detailed information"""
    profile = db.query(Profile).filter(Profile.user_id == id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Calculate user rank
    higher_ranked_count = db.query(Profile).filter(Profile.points > profile.points).count()
    user_rank = higher_ranked_count + 1
    
    # Get total number of users for percentile calculation
    total_users = db.query(Profile).count()
    percentile = round((1 - (user_rank / total_users)) * 100) if total_users > 0 else 0
    
    # Get completed quizzes count
    completed_quizzes = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.completed == True
    ).count()
    
    # Calculate days until next streak milestone
    next_milestone = 7 if profile.current_login_streak < 7 else 30
    days_to_milestone = next_milestone - (profile.current_login_streak % next_milestone)
    
    # Get streak bonus information from the session
    streak_bonus = request.session.get("streak_bonus", 0)
    
    # Clear the streak bonus from the session after reading it
    if streak_bonus:
        request.session.pop("streak_bonus", None)
    
    # Get followers and following counts
    followers_count = db.query(UserFollow).filter(UserFollow.followed_id == profile.id).count()
    following_count = db.query(UserFollow).filter(UserFollow.follower_id == profile.id).count()
    
    # Get followers and following (limited to 5 most recent)
    recent_followers = db.query(UserFollow).filter(UserFollow.followed_id == profile.id).order_by(desc(UserFollow.created_at)).limit(5).all()
    recent_following = db.query(UserFollow).filter(UserFollow.follower_id == profile.id).order_by(desc(UserFollow.created_at)).limit(5).all()
    
    # Check if current user is following this profile
    is_following = False
    if current_user.id != id:  # Don't check if viewing own profile
        current_user_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
        if current_user_profile:
            is_following = db.query(UserFollow).filter(
                UserFollow.follower_id == current_user_profile.id,
                UserFollow.followed_id == profile.id
            ).first() is not None
    
    # Format followers and following data
    followers_data = []
    for follow in recent_followers:
        follower_profile = follow.follower
        followers_data.append({
            "id": follower_profile.id,
            "nickname": follower_profile.nickname,
            "avatar_url": follower_profile.avatar_url,
            "user_id": follower_profile.user_id,
            "follow_date": follow.created_at
        })
    
    following_data = []
    for follow in recent_following:
        followed_profile = follow.followed
        following_data.append({
            "id": followed_profile.id,
            "nickname": followed_profile.nickname,
            "avatar_url": followed_profile.avatar_url,
            "user_id": followed_profile.user_id,
            "follow_date": follow.created_at
        })
    
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "is_admin": current_user.is_admin,
            "joined_at": current_user.joined_at
        },
        "profile": {
            "id": profile.id,
            "nickname": profile.nickname,
            "avatar_url": profile.avatar_url,
            "points": profile.points,
            "referral_code": profile.referral_code,
            "total_referrals": profile.total_referrals,
            "language_preference": profile.language_preference,
            "pronouns": profile.pronouns,
            "location": profile.location,
            "personalization_questions": profile.personalization_questions,
            "followers": {
                "count": followers_count,
                "recent": followers_data
            },
            "following": {
                "count": following_count,
                "recent": following_data
            },
            "is_following": is_following
        },
        "stats": {
            "rank": user_rank,
            "total_users": total_users,
            "percentile": percentile,
            "completed_quizzes": completed_quizzes,
            "current_login_streak": profile.current_login_streak,
            "max_login_streak": profile.max_login_streak,
            "days_to_next_milestone": days_to_milestone,
            "next_milestone": next_milestone,
            "streak_bonus": streak_bonus
        }
    }

@router.get("/user/streak")
async def get_user_streak(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current user's login streak information"""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Calculate days until next streak milestone
    next_milestone = 7 if profile.current_login_streak < 7 else 30
    days_to_milestone = next_milestone - (profile.current_login_streak % next_milestone)
    
    # Get streak bonus information from the session
    streak_bonus = request.session.get("streak_bonus", 0)
    current_streak = profile.current_login_streak
    
    # Calculate streak status
    streak_status = "active" if profile.last_login_date == date.today() else "inactive"
    
    # Calculate days since last login
    days_since_last_login = 0
    if profile.last_login_date:
        days_since_last_login = (date.today() - profile.last_login_date).days
    
    # Clear the streak bonus from the session after reading it
    if streak_bonus:
        request.session.pop("streak_bonus", None)
    
    return {
        "current_streak": current_streak,
        "max_streak": profile.max_login_streak,
        "streak_status": streak_status,
        "days_since_last_login": days_since_last_login,
        "days_to_next_milestone": days_to_milestone,
        "next_milestone": next_milestone,
        "streak_bonus": streak_bonus,
        "last_login_date": profile.last_login_date.isoformat() if profile.last_login_date else None
    }

@router.get("/notifications")
async def get_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notifications for the current user, including streak updates"""
    notifications = []
    
    # Check for streak bonus notification
    streak_bonus = request.session.get("streak_bonus", 0)
    current_streak = request.session.get("current_streak", 0)
    
    if streak_bonus > 0:
        # Create a notification for the streak bonus
        if current_streak == 7:
            notifications.append({
                "type": "streak_milestone",
                "title": "7-Day Streak Achieved!",
                "message": f"You've logged in for 7 days in a row! You earned a bonus of {streak_bonus} points.",
                "points": streak_bonus
            })
        elif current_streak == 30:
            notifications.append({
                "type": "streak_milestone",
                "title": "30-Day Streak Achieved!",
                "message": f"Amazing! You've logged in for 30 days in a row! You earned a bonus of {streak_bonus} points.",
                "points": streak_bonus
            })
        else:
            notifications.append({
                "type": "daily_login",
                "title": "Daily Login Bonus",
                "message": f"Thanks for coming back! You earned {streak_bonus} points for logging in today.",
                "points": streak_bonus
            })
        
        # Clear the notifications from the session after reading them
        request.session.pop("streak_bonus", None)
        request.session.pop("current_streak", None)
    
    # Get profile for streak information
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    # Check if the user is close to a streak milestone
    if profile and profile.current_login_streak > 0:
        if profile.current_login_streak == 6:
            notifications.append({
                "type": "streak_reminder",
                "title": "Almost There!",
                "message": "You're one day away from a 7-day streak and a 50-point bonus!",
                "streak": profile.current_login_streak
            })
        elif profile.current_login_streak == 29:
            notifications.append({
                "type": "streak_reminder",
                "title": "So Close!",
                "message": "You're one day away from a 30-day streak and a 200-point bonus!",
                "streak": profile.current_login_streak
            })
    
    return {
        "notifications": notifications,
        "unread_count": len(notifications)
    }





@router.post('/create-feedback')
async def create_feedback(
    data: FeedbackCreateModel,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_feedback= Feedback(
        text= data.text,
        user_id= current_user.id
    )
    db.add(new_feedback)
    try:
        db.commit()
        db.refresh(new_feedback)
        return JSONResponse({'detail': "Feedback Created"}, status_code=status.HTTP_201_CREATED)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/follow")
async def follow_user(
    data: FollowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Follow another user's profile"""
    # Get current user's profile
    follower_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not follower_profile:
        raise HTTPException(status_code=404, detail="Your profile not found")
    
    # Get the profile to follow
    followed_profile = db.query(Profile).filter(Profile.id == data.profile_id).first()
    if not followed_profile:
        raise HTTPException(status_code=404, detail="Profile to follow not found")
    
    # Check if trying to follow self
    if follower_profile.id == followed_profile.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    # Check if already following
    existing_follow = db.query(UserFollow).filter(
        UserFollow.follower_id == follower_profile.id,
        UserFollow.followed_id == followed_profile.id
    ).first()
    
    if existing_follow:
        raise HTTPException(status_code=400, detail="Already following this user")
    
    # Create the follow relationship
    new_follow = UserFollow(
        follower_id=follower_profile.id,
        followed_id=followed_profile.id
    )
    
    db.add(new_follow)
    try:
        db.commit()
        return {"message": "Successfully followed user"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/unfollow/{profile_id}")
async def unfollow_user(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Unfollow a user"""
    # Get current user's profile
    follower_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not follower_profile:
        raise HTTPException(status_code=404, detail="Your profile not found")
    
    # Find the follow relationship
    follow = db.query(UserFollow).filter(
        UserFollow.follower_id == follower_profile.id,
        UserFollow.followed_id == profile_id
    ).first()
    
    if not follow:
        raise HTTPException(status_code=404, detail="You are not following this user")
    
    # Delete the follow relationship
    db.delete(follow)
    try:
        db.commit()
        return {"message": "Successfully unfollowed user"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/followers/{profile_id}")
async def get_followers(
    profile_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all followers of a profile with pagination"""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Get followers with pagination
    follows = db.query(UserFollow).filter(
        UserFollow.followed_id == profile_id
    ).order_by(desc(UserFollow.created_at)).offset(skip).limit(limit).all()
    
    # Format response
    followers_data = []
    for follow in follows:
        follower_profile = follow.follower
        followers_data.append({
            "id": follower_profile.id,
            "nickname": follower_profile.nickname,
            "avatar_url": follower_profile.avatar_url,
            "user_id": follower_profile.user_id,
            "follow_date": follow.created_at
        })
    
    # Get total count
    total_count = db.query(UserFollow).filter(UserFollow.followed_id == profile_id).count()
    
    return {
        "followers": followers_data,
        "total": total_count,
        "skip": skip,
        "limit": limit
    }

@router.get("/following/{profile_id}")
async def get_following(
    profile_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users a profile is following with pagination"""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Get following with pagination
    follows = db.query(UserFollow).filter(
        UserFollow.follower_id == profile_id
    ).order_by(desc(UserFollow.created_at)).offset(skip).limit(limit).all()
    
    # Format response
    following_data = []
    for follow in follows:
        followed_profile = follow.followed
        following_data.append({
            "id": followed_profile.id,
            "nickname": followed_profile.nickname,
            "avatar_url": followed_profile.avatar_url,
            "user_id": followed_profile.user_id,
            "follow_date": follow.created_at
        })
    
    # Get total count
    total_count = db.query(UserFollow).filter(UserFollow.follower_id == profile_id).count()
    
    return {
        "following": following_data,
        "total": total_count,
        "skip": skip,
        "limit": limit
    }

@router.get("/search")
async def search_users(
    query: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search for users by username or nickname
    Flexible search that returns matches for either field
    """
    if not query or len(query.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters"
        )
    
    # Search for users with matching username or profiles with matching nickname
    # Using ILIKE for case-insensitive matching with wildcards
    search_pattern = f"%{query}%"
    
    # Query users and join with their profiles
    results = db.query(User, Profile).join(Profile, User.id == Profile.user_id).filter(
        (User.username.ilike(search_pattern)) | 
        (Profile.nickname.ilike(search_pattern))
    ).offset(skip).limit(limit).all()
    
    # Format the results
    users_data = []
    for user, profile in results:
        if user.id != current_user.id:  # Exclude current user from results
            # Check if current user is following this profile
            is_following = db.query(UserFollow).filter(
                UserFollow.follower_id == current_user.profile.id,
                UserFollow.followed_id == profile.id
            ).first() is not None
            
            users_data.append({
                "user_id": user.id,
                "username": user.username,
                "profile_id": profile.id,
                "nickname": profile.nickname,
                "avatar_url": profile.avatar_url,
                "is_following": is_following
            })
    
    # Count total matching results (without pagination)
    total_count = db.query(User, Profile).join(Profile, User.id == Profile.user_id).filter(
        (User.username.ilike(search_pattern)) | 
        (Profile.nickname.ilike(search_pattern))
    ).count()
    
    return {
        "users": users_data,
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "query": query
    }

@router.post('/resend-verification')
async def resend_verification(data: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Resend verification OTP to an existing user's email"""
    
    # Find the user by email
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found with this email"
        )
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )
    
    # Send verification OTP
    await send_verification_otp(user.email, db)
    
    return {"message": "Verification code sent. Please check your email."}

@router.get("/verification-status")
async def check_verification_status(current_user: User = Depends(get_current_user)):
    """Check if the current user's email is verified"""
    
    return {
        "is_verified": current_user.is_verified,
        "email": current_user.email,
        "message": "Your email is verified." if current_user.is_verified else "Your email is not verified. Please verify your email."
    }