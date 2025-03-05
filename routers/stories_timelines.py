from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from schemas.stories_timelines import (
    TimelineCreateModel, StoryCreateModel, OnThisDayCreateModel, OnThisDayResponseModel, 
    TimelineUpdateModel, StoryUpdateModel, TimeStampCreateModel, QuizCreateModel, 
    QuizResponseModel, QuestionCreateModel, OptionCreateModel, QuizUpdateModel
)
from db.models import get_db
from sqlalchemy.orm import Session
from db.models import User, Timeline, Story, OnThisDay, Timestamp, Quiz, Question, Option
from utils.auth import get_current_user, get_admin_user
from utils.file_handler import save_image, save_video, delete_file
from fastapi.responses import JSONResponse
from datetime import date
from typing import Optional, List
import json

router = APIRouter(
    prefix="/api"
)

@router.post('/otd/create')
async def create_otd(
    date: date = Form(...),
    title: str = Form(...),
    short_desc: str = Form(...),
    image_file: Optional[UploadFile] = File(None),
    story_id: Optional[int] = Form(None),
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Validate with Pydantic
    try:
        validated_data = OnThisDayCreateModel(
            date=date,
            title=title,
            short_desc=short_desc,
            story_id=story_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    # Save the image if provided
    image_url = await save_image(image_file) if image_file else None
    
    new_otd_obj = OnThisDay(
        date = validated_data.date,
        title = validated_data.title,
        short_desc = validated_data.short_desc,
        image_url = image_url,
        story_id = validated_data.story_id
    )
    
    db.add(new_otd_obj)
    try:
        db.commit()
        db.refresh(new_otd_obj)
        return {"id": new_otd_obj.id, "message": "On This Day entry created successfully"}
    except Exception as e:
        db.rollback()
        # Delete the uploaded file if there was an error
        if image_url:
            delete_file(image_url)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list/otd", response_model=list[OnThisDayResponseModel])
def get_all_otd(db: Session = Depends(get_db)):
    return db.query(OnThisDay).all()

@router.get("/{date}", response_model=OnThisDayResponseModel)
def get_otd_by_date(date: date, db: Session = Depends(get_db)):
    otd_entry = db.query(OnThisDay).filter(OnThisDay.date == date).first()
    if not otd_entry:
        raise HTTPException(status_code=404, detail="No historical event found for this date")
    return otd_entry

@router.delete("/{id}")
def delete_otd(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    otd_entry = db.query(OnThisDay).filter(OnThisDay.id == id).first()
    if not otd_entry:
        raise HTTPException(status_code=404, detail="OTD entry not found")
    
    # Store the image path before deleting the entry
    image_url = otd_entry.image_url
    
    db.delete(otd_entry)
    db.commit()
    
    # Delete the image file if it exists
    if image_url:
        delete_file(image_url)
    
    return {"message": "OTD entry deleted successfully"}

@router.post('/timeline/create')
async def create_timeline(
    title: str = Form(...),
    year_range: str = Form(...),
    overview: str = Form(...),
    thumbnail_file: UploadFile = File(...),
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Validate with Pydantic
    try:
        validated_data = TimelineCreateModel(
            title=title,
            year_range=year_range,
            overview=overview
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    # Save the thumbnail image
    thumbnail_url = await save_image(thumbnail_file)
    
    # Create new timeline using validated data
    new_timeline = Timeline(
        title = validated_data.title,
        thumbnail_url = thumbnail_url,
        year_range = validated_data.year_range,
        overview = validated_data.overview
    )
    
    db.add(new_timeline)
    try:
        db.commit()
        db.refresh(new_timeline)
        return JSONResponse({'detail': "Timeline Created", 'id': new_timeline.id}, status_code=status.HTTP_201_CREATED)
    except Exception as e:
        db.rollback()
        # Delete the uploaded file if there was an error
        if thumbnail_url:
            delete_file(thumbnail_url)
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/timeline/{timeline_id}')
async def get_timeline(timeline_id: int, db: Session= Depends(get_db), current_user: User= Depends(get_current_user)):
    timeline_obj= db.query(Timeline).filter(Timeline.id == timeline_id).first()
    if not timeline_obj:
        raise HTTPException(detail="TimeLine Not Found", status_code=status.HTTP_404_NOT_FOUND)
    
    return timeline_obj

@router.get('/list/timelines')
async def get_timelines(db: Session= Depends(get_db), current_user: User= Depends(get_current_user)):
    timelines= db.query(Timeline).all()
    return timelines

@router.patch('/timeline/update/{timeline_id}')
async def update_timeline(
    timeline_id: int,
    title: Optional[str] = Form(None),
    year_range: Optional[str] = Form(None),
    overview: Optional[str] = Form(None),
    thumbnail_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    timeline_query = db.query(Timeline).filter(Timeline.id == timeline_id)
    timeline_obj = timeline_query.first()
    
    if not timeline_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeline Not Found"
        )
    
    # Create update data dictionary
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if year_range is not None:
        update_data["year_range"] = year_range
    if overview is not None:
        update_data["overview"] = overview
    
    # Validate with Pydantic if there's data to update
    if update_data:
        try:
            # Only validate fields that are being updated
            validated_data = TimelineUpdateModel(**update_data)
            update_data = {k: v for k, v in validated_data.dict().items() if v is not None}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    # Handle thumbnail update
    old_thumbnail = None
    if thumbnail_file:
        old_thumbnail = timeline_obj.thumbnail_url
        update_data["thumbnail_url"] = await save_image(thumbnail_file)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )
    
    try:
        timeline_query.update(update_data, synchronize_session=False)
        db.commit()
        
        # Delete old thumbnail if it was replaced
        if old_thumbnail and thumbnail_file:
            delete_file(old_thumbnail)
            
        return JSONResponse(
            {'detail': 'Timeline updated successfully'},
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        db.rollback()
        # Delete the new thumbnail if there was an error
        if thumbnail_file and "thumbnail_url" in update_data:
            delete_file(update_data["thumbnail_url"])
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/timeline/{timeline_id}")
async def delete_timeline(
    timeline_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_admin_user)
):
    timeline_obj = db.query(Timeline).filter(Timeline.id == timeline_id).first()
    if not timeline_obj:
        raise HTTPException(detail="Timeline obj not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Store the thumbnail path before deleting the timeline
    thumbnail_url = timeline_obj.thumbnail_url
    
    # Get all stories to delete their files too
    stories = db.query(Story).filter(Story.timeline_id == timeline_id).all()
    story_files = [(story.thumbnail_url, story.video_url) for story in stories]
    
    db.delete(timeline_obj)
    try:
        db.commit()
        
        # Delete the thumbnail file
        if thumbnail_url:
            delete_file(thumbnail_url)
            
        # Delete all story files
        for thumbnail, video in story_files:
            if thumbnail:
                delete_file(thumbnail)
            if video:
                delete_file(video)
                
        return JSONResponse(
            {'detail': 'Timeline deleted successfully'},
            status_code=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{timeline}/story/create")
async def create_story(
    timeline: int,
    title: str = Form(...),
    desc: str = Form(...),
    timestamps_json: str = Form("[]"),
    thumbnail_file: UploadFile = File(...),
    video_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if the timeline exists
    current_timeline = db.query(Timeline).filter(Timeline.id == timeline).first()
    if not current_timeline:
        raise HTTPException(detail="Timeline not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Validate with Pydantic
    try:
        validated_data = StoryCreateModel(
            title=title,
            desc=desc,
            timeline_id=timeline
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    # Parse timestamps from JSON
    try:
        timestamps_data = json.loads(timestamps_json)
        # Validate each timestamp
        validated_timestamps = []
        for ts in timestamps_data:
            validated_timestamp = TimeStampCreateModel(**ts)
            validated_timestamps.append(validated_timestamp.dict())
        timestamps_data = validated_timestamps
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid timestamps JSON format")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Timestamp validation error: {str(e)}")
    
    # Save files
    thumbnail_url = await save_image(thumbnail_file)
    video_url = await save_video(video_file)
    
    # Create Story instance
    new_story = Story(
        title=validated_data.title,
        desc=validated_data.desc,
        thumbnail_url=thumbnail_url,
        video_url=video_url,
        timeline_id=current_timeline.id
    )
    
    db.add(new_story)
    try:
        db.commit()
        db.refresh(new_story)
        
        # Add timestamps
        timestamp_objects = [
            Timestamp(
                story_id=new_story.id,
                time_sec=ts.get("time_sec"),
                label=ts.get("label")
            )
            for ts in timestamps_data
        ]
        
        if timestamp_objects:
            db.add_all(timestamp_objects)
            db.commit()
            
        return new_story
    except Exception as e:
        db.rollback()
        # Delete uploaded files if there was an error
        if thumbnail_url:
            delete_file(thumbnail_url)
        if video_url:
            delete_file(video_url)
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/story/{story_id}')
async def get_story(story_id: int, db: Session= Depends(get_db), current_user: User= Depends(get_current_user)):
    story= db.query(Story).filter(Story.id == story_id).first()

    if not story:
        raise HTTPException(detail="Story not found", status_code=status.HTTP_404_NOT_FOUND)
    return story,story.timestamps

@router.get('/list/stories')
async def get_all_stories(db: Session= Depends(get_db), current_user: User= Depends(get_current_user)):
    all_stories= db.query(Story).all()
    return all_stories

@router.get('/timeline/{timeline_id}/stories')
async def get_stories_of_timeline(timeline_id: int, db: Session= Depends(get_db), current_user: User= Depends(get_current_user)):
    get_stories= db.query(Story).filter(Story.timeline_id == timeline_id).all()
    return get_stories

@router.patch('/story/update/{story_id}')
async def update_story(
    story_id: int,
    title: Optional[str] = Form(None),
    desc: Optional[str] = Form(None),
    timeline_id: Optional[int] = Form(None),
    timestamps_json: Optional[str] = Form(None),
    thumbnail_file: Optional[UploadFile] = File(None),
    video_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch the existing story
    story_query = db.query(Story).filter(Story.id == story_id)
    story_obj = story_query.first()

    if not story_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )

    # Create update data dictionary
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if desc is not None:
        update_data["desc"] = desc
    if timeline_id is not None:
        update_data["timeline_id"] = timeline_id
    
    # Validate with Pydantic if there's data to update
    if update_data:
        try:
            validated_data = StoryUpdateModel(**update_data)
            update_data = {k: v for k, v in validated_data.dict().items() if v is not None}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    # Handle file updates
    old_thumbnail = None
    old_video = None
    
    if thumbnail_file:
        old_thumbnail = story_obj.thumbnail_url
        update_data["thumbnail_url"] = await save_image(thumbnail_file)
        
    if video_file:
        old_video = story_obj.video_url
        update_data["video_url"] = await save_video(video_file)
    
    # Update story data if there's anything to update
    if update_data:
        story_query.update(update_data, synchronize_session=False)
    
    # Handle timestamps separately if provided
    if timestamps_json is not None:
        try:
            timestamps_data = json.loads(timestamps_json)
            
            # Validate timestamps
            validated_timestamps = []
            for ts in timestamps_data:
                validated_timestamp = TimeStampCreateModel(**ts)
                validated_timestamps.append({
                    "time_sec": validated_timestamp.time_sec,
                    "label": validated_timestamp.label
                })
            
            # Delete existing timestamps
            db.query(Timestamp).filter(Timestamp.story_id == story_id).delete()
            
            # Create new timestamps
            new_timestamps = [
                Timestamp(
                    story_id=story_id,
                    time_sec=ts["time_sec"],
                    label=ts["label"]
                )
                for ts in validated_timestamps
            ]
            
            if new_timestamps:
                db.bulk_save_objects(new_timestamps)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid timestamps JSON format")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Timestamp validation error: {str(e)}")
    
    try:
        db.commit()
        
        # Delete old files if they were replaced
        if old_thumbnail and thumbnail_file:
            delete_file(old_thumbnail)
        if old_video and video_file:
            delete_file(old_video)
            
        return JSONResponse(
            {'detail': 'Story updated successfully'},
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        db.rollback()
        # Delete new files if there was an error
        if thumbnail_file and "thumbnail_url" in update_data:
            delete_file(update_data["thumbnail_url"])
        if video_file and "video_url" in update_data:
            delete_file(update_data["video_url"])
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/story/delete/{story_id}")
async def delete_story(
    story_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_admin_user)
):
    story_obj = db.query(Story).filter(Story.id == story_id).first()
    if not story_obj:
        raise HTTPException(detail="Story obj not found", status_code=status.HTTP_404_NOT_FOUND)

    if not current_user.is_admin:
        raise HTTPException(detail="Only for admin", status_code=status.HTTP_401_UNAUTHORIZED)
    
    # Store file paths before deleting the story
    thumbnail_url = story_obj.thumbnail_url
    video_url = story_obj.video_url
    
    db.delete(story_obj)
    try:
        db.commit()
        
        # Delete the files
        if thumbnail_url:
            delete_file(thumbnail_url)
        if video_url:
            delete_file(video_url)
            
        return JSONResponse(
            {'detail': 'Story deleted successfully'},
            status_code=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/story/{story_id}/quiz/create', response_model=QuizResponseModel)
async def create_quiz(
    story_id: int,
    quiz_data: QuizCreateModel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if the story exists
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Check if the story already has a quiz
    existing_quiz = db.query(Quiz).filter(Quiz.story_id == story_id).first()
    if existing_quiz:
        raise HTTPException(status_code=400, detail="This story already has a quiz")
    
    try:
        # Create the quiz
        quiz = Quiz(story_id=story_id)
        db.add(quiz)
        db.flush()  # Flush to get the quiz ID
        
        # Create questions and options
        for question_data in quiz_data.questions:
            question = Question(
                quiz_id=quiz.id,
                text=question_data.text
            )
            db.add(question)
            db.flush()  # Flush to get the question ID
            
            # Create options for the question
            for option_data in question_data.options:
                option = Option(
                    question_id=question.id,
                    text=option_data.text,
                    is_correct=option_data.is_correct
                )
                db.add(option)
        
        db.commit()
        db.refresh(quiz)
        
        return quiz
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/story/{story_id}/quiz', response_model=QuizResponseModel)
async def get_quiz_by_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if the story exists
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Get the quiz
    quiz = db.query(Quiz).filter(Quiz.story_id == story_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found for this story")
    
    return quiz

@router.get('/quiz/{quiz_id}', response_model=QuizResponseModel)
async def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    return quiz

@router.get('/list/quizzes', response_model=List[QuizResponseModel])
async def get_all_quizzes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    quizzes = db.query(Quiz).all()
    return quizzes

@router.patch('/quiz/{quiz_id}', response_model=QuizResponseModel)
async def update_quiz(
    quiz_id: int,
    quiz_data: QuizUpdateModel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if the quiz exists
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Only update questions if provided
    if quiz_data.questions is not None:
        try:
            # Delete existing questions and options
            db.query(Question).filter(Question.quiz_id == quiz_id).delete()
            db.flush()
            
            # Create new questions and options
            for question_data in quiz_data.questions:
                question = Question(
                    quiz_id=quiz.id,
                    text=question_data.text
                )
                db.add(question)
                db.flush()  # Flush to get the question ID
                
                # Create options for the question
                for option_data in question_data.options:
                    option = Option(
                        question_id=question.id,
                        text=option_data.text,
                        is_correct=option_data.is_correct
                    )
                    db.add(option)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
    
    db.commit()
    db.refresh(quiz)
    
    return quiz

@router.delete('/quiz/{quiz_id}')
async def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    # Check if the quiz exists
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Delete the quiz (cascade will delete questions and options)
    db.delete(quiz)
    db.commit()
    
    return {"message": "Quiz deleted successfully"}