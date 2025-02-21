from fastapi import APIRouter,Depends,Request, HTTPException,status
from db.models import get_db,User,Profile
from sqlalchemy.orm import Session
from schemas.users import UserCreateModel, LoginModel,ProfileUpdate,UserEmailUpdate, UserPasswordChange
from fastapi.responses import JSONResponse
from db.models import pwd_context

from utils.auth import get_current_user, create_session, end_session

router= APIRouter(prefix="/api/auth")

@router.post('/create-user')
async def create_user(request: Request, data: UserCreateModel, db: Session = Depends(get_db)):
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )


    elif db.query(User).filter(User.email == data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    elif len(data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
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
async def delete_user(current_user: User = Depends(get_current_user), db: Session= Depends(get_db)):
    my_user= db.query(User).filter(User.id == current_user.id).first()
    if not my_user:
        return HTTPException(detail="User not found, Unexpected error",status_code=status.HTTP_404_NOT_FOUND)
    db.delete(my_user)
    db.commit()
    return JSONResponse({'detail': "User deleted"}, status_code=status.HTTP_204_NO_CONTENT)


@router.post("/login")
async def login(request: Request, data: LoginModel, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user or not user.verify_password(data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create session
    create_session(request, user)
    
    return {
        "user": {
            "id": user.id,
            "email": user.email,
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
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ Fix: Use `.first()` to get the actual Profile instance
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # ✅ Only update fields that are provided in the request
    update_data = profile_data.dict(exclude_unset=True)  

    # ✅ Apply updates dynamically
    for key, value in update_data.items():
        setattr(profile, key, value)

    # ✅ Save changes to the DB
    db.commit()
    db.refresh(profile)

    return update_data  # Uses `UserResponse` for structured output


@router.get("/user/me")
async def profile(current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    my_profile= db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not my_profile:
        return HTTPException(detail="User Not Found", status_code=status.HTTP_404_NOT_FOUND)
    
    return my_profile


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