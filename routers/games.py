from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Path
from db.models import get_db, StandAloneGameQuestion, StandAloneGameOption, StandAloneGameAttempt, GameTypes, User
from sqlalchemy.orm import Session
from utils.file_handler import save_image, delete_file
from schemas.games import (
    GameQuestion, 
    GameAttemptCreate, GameAttempt, PaginatedGames, GameOptionCreate
)
from typing import List, Optional
from utils.auth import get_current_user
import math
import os
import json

router= APIRouter(prefix="/api/game")

# Create a single game question with direct file upload
@router.post("/questions", response_model=GameQuestion, status_code=status.HTTP_201_CREATED)
async def create_game_question(
    title: str = Form(...),
    game_type: int = Form(...),
    options_json: str = Form(...),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):    
    # Parse options from JSON
    try:
        options_data = json.loads(options_json)
        # Validate options
        validated_options = []
        for option in options_data:
            validated_option = GameOptionCreate(**option)
            validated_options.append(validated_option)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid options format: {str(e)}"
        )
    
    # Save image if provided
    image_url = await save_image(image_file) if image_file else None
    
    # Create the game question
    new_question = StandAloneGameQuestion(
        title=title,
        game_type=game_type,
        image_url=image_url
    )
    print(new_question)
    db.add(new_question)
    db.flush()
    
    # Add options
    for option in validated_options:
        new_option = StandAloneGameOption(
            question_id=new_question.id,
            text=option.text,
            is_correct=option.is_correct
        )
        db.add(new_option)
    
    try:
        db.commit()
        db.refresh(new_question)
        return new_question
    except Exception as e:
        db.rollback()
        # Delete the uploaded file if there was an error
        if image_url:
            delete_file(image_url)
        raise HTTPException(status_code=400, detail=str(e))

# Bulk create game questions
@router.post("/questions/bulk", response_model=List[GameQuestion], status_code=status.HTTP_201_CREATED)
async def create_bulk_game_questions(
    game_type: int = Form(...),
    questions_json: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):  
    # Parse questions from JSON
    try:
        questions_data = json.loads(questions_json)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format for questions"
        )
    
    created_questions = []
    
    try:
        for question_data in questions_data:
            new_question = StandAloneGameQuestion(
                title=question_data.get("title"),
                game_type=game_type,
                image_url=question_data.get("image_url")
            )
            
            db.add(new_question)
            db.flush()
            
            # Add options
            for option_data in question_data.get("options", []):
                new_option = StandAloneGameOption(
                    question_id=new_question.id,
                    text=option_data.get("text"),
                    is_correct=option_data.get("is_correct", False)
                )
                db.add(new_option)
            
            db.flush()
            created_questions.append(new_question)
        
        db.commit()
        return created_questions
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# Get games with pagination
@router.get("/questions", response_model=PaginatedGames)
async def get_games(
    game_type: Optional[GameTypes] = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(StandAloneGameQuestion)
    
    if game_type:
        query = query.filter(StandAloneGameQuestion.game_type == game_type)
    
    total = query.count()
    pages = math.ceil(total / size)
    
    items = query.order_by(StandAloneGameQuestion.created_at.desc()) \
                .offset((page - 1) * size) \
                .limit(size) \
                .all()
    
    return {
        "total": total,
        "items": items,
        "page": page,
        "size": size,
        "pages": pages
    }

# Get single game by ID
@router.get("/questions/{question_id}", response_model=GameQuestion)
async def get_game_by_id(
    question_id: int = Path(...),
    db: Session = Depends(get_db)
):
    question = db.query(StandAloneGameQuestion).filter(StandAloneGameQuestion.id == question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game question not found"
        )
    
    return question

# Update game question with direct file upload
@router.patch("/questions/{question_id}", response_model=GameQuestion)
async def update_game_question(
    question_id: int = Path(...),
    title: Optional[str] = Form(None),
    game_type: Optional[int] = Form(None), 
    options_json: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    question = db.query(StandAloneGameQuestion).filter(StandAloneGameQuestion.id == question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game question not found"
        )
    
    # Update basic fields if provided
    if title is not None:
        question.title = title
    
    if game_type is not None:
        question.game_type = game_type
    
    # Handle image file update
    old_image_url = None
    if image_file:
        old_image_url = question.image_url
        question.image_url = await save_image(image_file, folder_path="media/game-images")
    
    # Update options if provided
    if options_json:
        try:
            options_data = json.loads(options_json)
            
            # Delete existing options
            db.query(StandAloneGameOption).filter(StandAloneGameOption.question_id == question_id).delete()
            
            # Add new options
            for option_data in options_data:
                new_option = StandAloneGameOption(
                    question_id=question_id,
                    text=option_data.get("text"),
                    is_correct=option_data.get("is_correct", False)
                )
                db.add(new_option)
                
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format for options"
            )
    
    try:
        db.commit()
        db.refresh(question)
        
        # Delete old image if it was replaced
        if old_image_url and image_file:
            delete_file(old_image_url)
            
        return question
    except Exception as e:
        db.rollback()
        # Delete new image if there was an error
        if image_file and question.image_url != old_image_url:
            delete_file(question.image_url)
        raise HTTPException(status_code=400, detail=str(e))

# Delete game question
@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game_question(
    question_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    question = db.query(StandAloneGameQuestion).filter(StandAloneGameQuestion.id == question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game question not found"
        )
    
    # Store image path before deleting
    image_url = question.image_url
    
    db.delete(question)
    try:
        db.commit()
        
        # Delete associated image if exists
        if image_url and os.path.exists(image_url):
            delete_file(image_url)
        
        return
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# Submit game attempt
@router.post("/attempt", response_model=GameAttempt, status_code=status.HTTP_201_CREATED)
async def submit_game_attempt(
    attempt: GameAttemptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify the game exists
    game = db.query(StandAloneGameQuestion).filter(StandAloneGameQuestion.id == attempt.standalone_question_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game question not found"
        )
    
    # Verify the option exists and belongs to the game
    option = db.query(StandAloneGameOption).filter(
        StandAloneGameOption.id == attempt.selected_option_id,
        StandAloneGameOption.question_id == attempt.standalone_question_id
    ).first()
    
    if not option:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected option not found or does not belong to this game"
        )
    
    # Create the attempt record
    new_attempt = StandAloneGameAttempt(
        user_id=current_user.id,
        game_id=attempt.standalone_question_id,
        selected_option_id=attempt.selected_option_id,
        is_correct=option.is_correct
    )
    
    db.add(new_attempt)
    db.commit()
    db.refresh(new_attempt)
    
    # Award points if the answer is correct (similar to quiz system)
    if option.is_correct:
        profile = current_user.profile
        profile.points += 5  # Award 5 points for correct answers
        db.commit()
    
    return new_attempt

# Get user's game attempts
@router.get("/attempts", response_model=List[GameAttempt])
async def get_user_attempts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attempts = db.query(StandAloneGameAttempt).filter(
        StandAloneGameAttempt.user_id == current_user.id
    ).order_by(StandAloneGameAttempt.created_at.desc()).all()
    
    return attempts

