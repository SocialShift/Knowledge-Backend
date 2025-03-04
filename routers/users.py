from fastapi import APIRouter, Depends, Request, HTTPException, status, UploadFile, File, Form
from db.models import get_db, User, Profile
from sqlalchemy.orm import Session
from schemas.users import UserCreateModel, LoginModel, ProfileUpdate, UserEmailUpdate, UserPasswordChange
from fastapi.responses import JSONResponse
from db.models import pwd_context
from utils.auth import get_current_user, create_session, end_session
from utils.file_handler import save_image, delete_file
from typing import Optional
import json

router = APIRouter(prefix="/api/auth")

@router.post('/create-user')
async def create_user(
    request: Request, 
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Validate with Pydantic
    try:
        validated_data = UserCreateModel(
            email=email,
            password=password,
            confirm_password=confirm_password
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")

    if validated_data.password != validated_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    elif db.query(User).filter(User.email == validated_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    elif len(validated_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Your success logic here
    new_user = User(
        email=validated_data.email
    )
    new_user.set_password(validated_data.password)
    
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    
    new_profile = Profile(user_id=new_user.id)
    db.add(new_profile)
    try:
        db.commit()
        db.refresh(new_profile)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    # Create session for the new user
    create_session(request, new_user)
    
    return JSONResponse({
        'detail': 'New User created',
        'user': {
            'id': new_user.id,
            'email': new_user.email
        }
    }, status_code=status.HTTP_201_CREATED)

@router.delete('/delete-user')
async def delete_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    my_user = db.query(User).filter(User.id == current_user.id).first()
    if not my_user:
        return HTTPException(detail="User not found, Unexpected error", status_code=status.HTTP_404_NOT_FOUND)
    db.delete(my_user)
    db.commit()
    return JSONResponse({'detail': "User deleted"}, status_code=status.HTTP_204_NO_CONTENT)

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Validate with Pydantic
    try:
        validated_data = LoginModel(
            email=email,
            password=password
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    user = db.query(User).filter(User.email == validated_data.email).first()
    
    if not user or not user.verify_password(validated_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create session
    create_session(request, user)
    
    return {
        "user": {
            "id": user.id,
            "email": user.email
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
    personalization_questions_json: str = Form(None),
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
    if personalization_questions_json is not None:
        try:
            update_data["personalization_questions"] = json.loads(personalization_questions_json)
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

@router.get("/user/me")
async def profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    my_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not my_profile:
        return HTTPException(detail="User Not Found", status_code=status.HTTP_404_NOT_FOUND)
    
    return my_profile

@router.patch("/profile/update/user-email")
async def update_user_profile(
    email: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate with Pydantic
    try:
        validated_data = UserEmailUpdate(email=email)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    my_user = db.query(User).filter(User.id == current_user.id).first()

    if not my_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if db.query(User).filter(User.email == validated_data.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    # Update the email
    my_user.email = validated_data.email

    db.commit()
    db.refresh(my_user)

    return {"message": "Email updated successfully", "email": my_user.email}

@router.post('/change-password')
async def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_new_password: str = Form(...),
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Validate with Pydantic
    try:
        validated_data = UserPasswordChange(
            current_password=current_password,
            new_password=new_password,
            confirm_new_password=confirm_new_password
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    # Fetch the user instance
    my_user = db.query(User).filter(User.id == current_user.id).first()

    if not my_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User Not Found"
        )
    
    # Verify current password
    if not pwd_context.verify(validated_data.current_password, my_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )

    # Check if new passwords match
    if validated_data.new_password != validated_data.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and Confirm Password didn't match"
        )

    # Hash new password and update user
    my_user.password = pwd_context.hash(validated_data.new_password)
    
    db.commit()
    db.refresh(my_user)

    return {"message": "Password changed successfully."}