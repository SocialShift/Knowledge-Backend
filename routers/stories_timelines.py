from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Query
from schemas.stories_timelines import (
    TimelineCreateModel, StoryCreateModel, OnThisDayCreateModel, OnThisDayResponseModel, 
    TimelineUpdateModel, StoryUpdateModel, TimeStampCreateModel, QuizCreateModel, 
    QuizResponseModel, QuestionCreateModel, OptionCreateModel, QuizUpdateModel, QuizSubmissionModel,
    QuizAttemptResponseModel, CharacterCreateModel, CharacterUpdateModel, CharacterResponseModel
)
from schemas.users import LeaderboardEntryModel, LeaderboardResponseModel
from db.models import get_db
from sqlalchemy.orm import Session
from db.models import User, Timeline, Story, OnThisDay, Timestamp, Quiz, Question, Option, Profile, QuizAttempt, StoryType, UserStoryLike, Character
from utils.auth import get_current_user, get_admin_user
from utils.file_handler import save_image, save_video, delete_file
from fastapi.responses import JSONResponse
from datetime import date, datetime
from typing import Optional, List
import json
import re

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

@router.get("/list/otd")
async def get_all_otd(db: Session = Depends(get_db)):
    otd_entries = db.query(OnThisDay).all()
    return otd_entries
    # Convert each entry to a dictionary with proper None handling
    #return [otd_to_dict(entry) for entry in otd_entries]

@router.get('/leaderboard', response_model=LeaderboardResponseModel)
async def get_leaderboard(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the top users by points"""
    # Query profiles ordered by points (descending)
    top_profiles = db.query(
        Profile.id,
        Profile.user_id,
        Profile.nickname,
        Profile.avatar_url,
        Profile.points,
        Profile.current_login_streak,
        Profile.max_login_streak,
        User.email
    ).join(User).order_by(Profile.points.desc()).limit(limit).all()
    
    # Format the results
    leaderboard = []
    for i, profile in enumerate(top_profiles):
        # Create a dictionary with the profile data
        profile_dict = LeaderboardEntryModel(
            rank=i + 1,
            user_id=profile.user_id,
            nickname=profile.nickname or profile.email.split('@')[0],  # Use email username if no nickname
            avatar_url=profile.avatar_url,
            points=profile.points,
            current_streak=profile.current_login_streak,
            max_streak=profile.max_login_streak
        )
        leaderboard.append(profile_dict)
    
    # Get the current user's rank
    user_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    user_rank = None
    
    if user_profile:
        higher_ranked_count = db.query(Profile).filter(Profile.points > user_profile.points).count()
        user_rank = higher_ranked_count + 1
    
    return LeaderboardResponseModel(
        leaderboard=leaderboard,
        user_rank=user_rank
    )

@router.get('/user/rank')
async def get_user_rank(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current user's rank based on points"""
    # Get the current user's profile
    user_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not user_profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Count how many users have more points than the current user
    higher_ranked_count = db.query(Profile).filter(Profile.points > user_profile.points).count()
    
    # The user's rank is the count of users with more points + 1
    user_rank = higher_ranked_count + 1
    
    # Get total number of users for percentile calculation
    total_users = db.query(Profile).count()
    percentile = round((1 - (user_rank / total_users)) * 100) if total_users > 0 else 0
    
    return {
        "rank": user_rank,
        "total_users": total_users,
        "percentile": percentile,
        "points": user_profile.points,
        "current_streak": user_profile.current_login_streak,
        "max_streak": user_profile.max_login_streak
    }

@router.get("/otd/date/{date}")
async def get_otd_by_date(date: date, db: Session = Depends(get_db)):
    otd_entry = db.query(OnThisDay).filter(OnThisDay.date == date).first()
    if not otd_entry:
        raise HTTPException(status_code=404, detail="No historical event found for this date")
    
    # Convert to dictionary with proper None handling
    return (otd_entry)

@router.delete("/otd/{id}")
async def delete_otd(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
    main_character_id: Optional[int] = Form(None),
    categories_json: Optional[str] = Form("[]"),
    thumbnail_file: UploadFile = File(...),
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Validate with Pydantic
    try:
        # Parse categories from JSON if provided
        categories = []
        if categories_json and categories_json.strip():
            try:
                categories = json.loads(categories_json)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid categories JSON format")
        
        validated_data = TimelineCreateModel(
            title=title,
            year_range=year_range,
            overview=overview,
            main_character_id=main_character_id,
            categories=categories
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
        overview = validated_data.overview,
        main_character_id = validated_data.main_character_id,
        categories = validated_data.categories
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
    
    # Get main character info if exists
    main_character = None
    if timeline_obj.main_character_id:
        character = db.query(Character).filter(Character.id == timeline_obj.main_character_id).first()
        if character:
            main_character = {
                "id": character.id,
                "avatar_url": character.avatar_url,
                "persona": character.persona,
                "created_at": character.created_at
            }
    
    # Create response with timeline and main character
    response = {
        "id": timeline_obj.id,
        "title": timeline_obj.title,
        "year_range": timeline_obj.year_range,
        "overview": timeline_obj.overview,
        "thumbnail_url": timeline_obj.thumbnail_url,
        "created_at": timeline_obj.created_at,
        "main_character": main_character,
        "categories": timeline_obj.categories
    }
    
    return response

@router.get('/list/timelines')
async def get_timelines(db: Session= Depends(get_db), current_user: User= Depends(get_current_user)):
    timelines = db.query(Timeline).all()
    
    # Convert each timeline to a dictionary with categories included
    result = []
    for timeline in timelines:
        # Get main character info if exists
        main_character = None
        if timeline.main_character_id:
            character = db.query(Character).filter(Character.id == timeline.main_character_id).first()
            if character:
                main_character = {
                    "id": character.id,
                    "avatar_url": character.avatar_url,
                    "persona": character.persona,
                    "created_at": character.created_at
                }
        
        # Create response with timeline and main character
        timeline_dict = {
            "id": timeline.id,
            "title": timeline.title,
            "year_range": timeline.year_range,
            "overview": timeline.overview,
            "thumbnail_url": timeline.thumbnail_url,
            "created_at": timeline.created_at,
            "main_character": main_character,
            "categories": timeline.categories
        }
        result.append(timeline_dict)
    
    return result

@router.get('/timelines/filter')
async def filter_timelines(
    categories: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Filter timelines by categories"""
    query = db.query(Timeline)
    
    if categories:
        # Filter timelines that have at least one matching category
        # This is a more complex query since we need to filter based on JSON array contents
        filtered_timelines = []
        all_timelines = query.all()
        
        for timeline in all_timelines:
            if timeline.categories:
                # Check if any specified category is in the timeline's categories
                if any(category in timeline.categories for category in categories):
                    filtered_timelines.append(timeline)
    else:
        # If no categories specified, return all timelines
        filtered_timelines = query.all()
    
    # Convert timelines to response format with categories included
    result = []
    for timeline in filtered_timelines:
        # Get main character info if exists
        main_character = None
        if timeline.main_character_id:
            character = db.query(Character).filter(Character.id == timeline.main_character_id).first()
            if character:
                main_character = {
                    "id": character.id,
                    "avatar_url": character.avatar_url,
                    "persona": character.persona,
                    "created_at": character.created_at
                }
        
        # Create response with timeline and main character
        timeline_dict = {
            "id": timeline.id,
            "title": timeline.title,
            "year_range": timeline.year_range,
            "overview": timeline.overview,
            "thumbnail_url": timeline.thumbnail_url,
            "created_at": timeline.created_at,
            "main_character": main_character,
            "categories": timeline.categories
        }
        result.append(timeline_dict)
    
    return result

@router.patch('/timeline/update/{timeline_id}')
async def update_timeline(
    timeline_id: int,
    title: Optional[str] = Form(None),
    year_range: Optional[str] = Form(None),
    overview: Optional[str] = Form(None),
    main_character_id: Optional[int] = Form(None),
    categories_json: Optional[str] = Form("[]"),
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
    if main_character_id is not None:
        update_data["main_character_id"] = main_character_id
    
    # Parse categories from JSON if provided
    if categories_json is not None:
        try:
            update_data["categories"] = json.loads(categories_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid categories JSON format")
    
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
    current_user: User = Depends(get_current_user)
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
    story_date: date= Form(...),
    story_type: Optional[int] = Form(None),
    timestamps_json: str = Form("[]"),
    thumbnail_file: UploadFile = File(...),
    video_file: Optional[UploadFile] = File(...),
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
            timeline_id=timeline,
            story_date=story_date,
            story_type=story_type
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    # Parse timestamps from JSON
    try:
        print("Raw timestamps_json:", timestamps_json)
        print("Type of timestamps_json:", type(timestamps_json))
        
        # Special handling for the format in the example
        if "{:" in timestamps_json and "}:" in timestamps_json:
            # Extract the actual JSON part using regex
            match = re.search(r'"timestamps_json":\s*(\[.*?\])', timestamps_json)
            if match:
                timestamps_json = match.group(1)
                print("Extracted timestamps_json:", timestamps_json)
        
        # Try to clean the JSON string if it has extra characters
        if timestamps_json.startswith("{:") and timestamps_json.endswith("}:"):
            # Extract the actual JSON part
            timestamps_json = timestamps_json[2:-2].strip()
            print("Cleaned timestamps_json:", timestamps_json)
        
        timestamps_data = json.loads(timestamps_json)
        print("Parsed timestamps data:", timestamps_data)
        print("Type of parsed data:", type(timestamps_data))
        
        # Validate each timestamp
        validated_timestamps = []
        for ts in timestamps_data:
            print("Processing timestamp:", ts)
            validated_timestamp = TimeStampCreateModel(**ts)
            validated_timestamps.append(validated_timestamp.dict())
        timestamps_data = validated_timestamps
    except json.JSONDecodeError as e:
        print("JSON decode error:", str(e))
        
        # Try one more approach - if the string contains the timestamps directly
        try:
            # Example format: '[{"time_sec": 233, "label": "y3rfyireiefry"},{"time_sec":2332, "label": "bhyerfhrefih"}]'
            if "[{" in timestamps_json and "}]" in timestamps_json:
                start_idx = timestamps_json.find("[{")
                end_idx = timestamps_json.find("}]") + 2
                extracted_json = timestamps_json[start_idx:end_idx]
                print("Extracted JSON from string:", extracted_json)
                
                timestamps_data = json.loads(extracted_json)
                print("Successfully parsed extracted JSON:", timestamps_data)
                
                # Validate each timestamp
                validated_timestamps = []
                for ts in timestamps_data:
                    validated_timestamp = TimeStampCreateModel(**ts)
                    validated_timestamps.append(validated_timestamp.dict())
                timestamps_data = validated_timestamps
            else:
                raise HTTPException(status_code=400, detail=f"Invalid timestamps JSON format: {str(e)}")
        except Exception as inner_e:
            print("Failed second attempt to parse JSON:", str(inner_e))
            raise HTTPException(status_code=400, detail=f"Invalid timestamps JSON format: {str(e)}")
    except Exception as e:
        print("Other timestamp error:", str(e))
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
        timeline_id=current_timeline.id,
        story_date=validated_data.story_date,
        story_type=validated_data.story_type
    )
    
    db.add(new_story)
    try:
        db.commit()
        db.refresh(new_story)
        
        # Add timestamps - create them one by one for better debugging
        for ts in timestamps_data:
            timestamp = Timestamp(
                story_id=new_story.id,
                time_sec=ts["time_sec"],
                label=ts["label"]
            )
            print(f"Creating timestamp: {timestamp.time_sec}, {timestamp.label} for story {timestamp.story_id}")
            db.add(timestamp)
        
        # Commit the timestamps
        db.commit()
        
        # Verify timestamps were created
        created_timestamps = db.query(Timestamp).filter(Timestamp.story_id == new_story.id).all()
        print(f"Created {len(created_timestamps)} timestamps for story {new_story.id}")
        
        # Return story with timestamps
        return {
            "story": {
                "id": new_story.id,
                "title": new_story.title,
                "desc": new_story.desc,
                "thumbnail_url": new_story.thumbnail_url,
                "video_url": new_story.video_url,
                "timeline_id": new_story.timeline_id,
                "story_date": new_story.story_date,
                "story_type": new_story.story_type,
                "views": new_story.views,
                "likes": new_story.likes,
                "created_at": new_story.created_at
            },
            "timestamps": [
                {
                    "id": ts.id,
                    "story_id": ts.story_id,
                    "time_sec": ts.time_sec,
                    "label": ts.label
                } for ts in created_timestamps
            ]
        }
    except Exception as e:
        print("Error during story/timestamp creation:", str(e))
        db.rollback()
        # Delete uploaded files if there was an error
        if thumbnail_url:
            delete_file(thumbnail_url)
        if video_url:
            delete_file(video_url)
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/story/{story_id}')
async def get_story(story_id: int, db: Session= Depends(get_db), current_user: User= Depends(get_current_user)):
    story = db.query(Story).filter(Story.id == story_id).first()

    if not story:
        raise HTTPException(detail="Story not found", status_code=status.HTTP_404_NOT_FOUND)
    # Increment the view count
    story.views += 1
    db.commit()  # Commit the change to the database
    
    # Get timestamps for this story
    timestamps = db.query(Timestamp).filter(Timestamp.story_id == story_id).all()
    
    # Create a response dictionary with story and timestamps as structured data
    response = {
        "story": {
            "id": story.id,
            "title": story.title,
            "desc": story.desc,
            "thumbnail_url": story.thumbnail_url,
            "video_url": story.video_url,
            "timeline_id": story.timeline_id,
            "story_date": story.story_date,
            "story_type": story.story_type,
            "views": story.views,
            "likes": story.likes,
            "created_at": story.created_at
        },
        "timestamps": [
            {
                "id": ts.id,
                "story_id": ts.story_id,
                "time_sec": ts.time_sec,
                "label": ts.label
            } for ts in timestamps
        ]
    }
    
    return response

@router.get('/list/stories')
async def get_all_stories(db: Session= Depends(get_db), current_user: User= Depends(get_current_user)):
    all_stories = db.query(Story).all()
    
    # Create a list of stories with their timestamps
    stories_with_timestamps = []
    for story in all_stories:
        timestamps = db.query(Timestamp).filter(Timestamp.story_id == story.id).all()
        stories_with_timestamps.append({
            "story": {
                "id": story.id,
                "title": story.title,
                "desc": story.desc,
                "thumbnail_url": story.thumbnail_url,
                "video_url": story.video_url,
                "timeline_id": story.timeline_id,
                "story_date": story.story_date,
                "story_type": story.story_type,
                "views": story.views,
                "likes": story.likes,
                "created_at": story.created_at
            },
            "timestamps": [
                {
                    "id": ts.id,
                    "story_id": ts.story_id,
                    "time_sec": ts.time_sec,
                    "label": ts.label
                } for ts in timestamps
            ]
        })
    
    return stories_with_timestamps

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
    story_date: Optional[date] = Form(None),
    story_type: Optional[int] = Form(None),
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
    if story_date is not None:
        update_data["story_date"] = story_date
    if story_type is not None:
        update_data["story_type"] = story_type
    
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
            print("Raw timestamps_json:", timestamps_json)
            print("Type of timestamps_json:", type(timestamps_json))
            
            # Special handling for the format in the example
            if "{:" in timestamps_json and "}:" in timestamps_json:
                # Extract the actual JSON part using regex
                match = re.search(r'"timestamps_json":\s*(\[.*?\])', timestamps_json)
                if match:
                    timestamps_json = match.group(1)
                    print("Extracted timestamps_json:", timestamps_json)
            
            # Try to clean the JSON string if it has extra characters
            if timestamps_json.startswith("{:") and timestamps_json.endswith("}:"):
                # Extract the actual JSON part
                timestamps_json = timestamps_json[2:-2].strip()
                print("Cleaned timestamps_json:", timestamps_json)
            
            timestamps_data = json.loads(timestamps_json)
            print("Parsed timestamps data:", timestamps_data)
            print("Type of parsed data:", type(timestamps_data))
            
            # Validate timestamps
            validated_timestamps = []
            for ts in timestamps_data:
                print("Processing timestamp:", ts)
                validated_timestamp = TimeStampCreateModel(**ts)
                validated_timestamps.append(validated_timestamp.dict())
            
        except json.JSONDecodeError as e:
            print("JSON decode error:", str(e))
            
            # Try one more approach - if the string contains the timestamps directly
            try:
                # Example format: '[{"time_sec": 233, "label": "y3rfyireiefry"},{"time_sec":2332, "label": "bhyerfhrefih"}]'
                if "[{" in timestamps_json and "}]" in timestamps_json:
                    start_idx = timestamps_json.find("[{")
                    end_idx = timestamps_json.find("}]") + 2
                    extracted_json = timestamps_json[start_idx:end_idx]
                    print("Extracted JSON from string:", extracted_json)
                    
                    timestamps_data = json.loads(extracted_json)
                    print("Successfully parsed extracted JSON:", timestamps_data)
                    
                    # Validate each timestamp
                    validated_timestamps = []
                    for ts in timestamps_data:
                        validated_timestamp = TimeStampCreateModel(**ts)
                        validated_timestamps.append(validated_timestamp.dict())
                else:
                    raise HTTPException(status_code=400, detail=f"Invalid timestamps JSON format: {str(e)}")
            except Exception as inner_e:
                print("Failed second attempt to parse JSON:", str(inner_e))
                raise HTTPException(status_code=400, detail=f"Invalid timestamps JSON format: {str(e)}")
        except Exception as e:
            print("Other timestamp error:", str(e))
            raise HTTPException(status_code=400, detail=f"Timestamp validation error: {str(e)}")
            
        # Delete existing timestamps
        db.query(Timestamp).filter(Timestamp.story_id == story_id).delete()
        
        # Create new timestamps one by one for better debugging
        for ts in validated_timestamps:
            timestamp = Timestamp(
                story_id=story_id,
                time_sec=ts["time_sec"],
                label=ts["label"]
            )
            print(f"Creating timestamp: {timestamp.time_sec}, {timestamp.label} for story {timestamp.story_id}")
            db.add(timestamp)
        
        print(f"Created {len(validated_timestamps)} updated timestamps")
    
    try:
        db.commit()
        
        # Delete old files if they were replaced
        if old_thumbnail and thumbnail_file:
            delete_file(old_thumbnail)
        if old_video and video_file:
            delete_file(old_video)
            
        # Get the updated story with timestamps
        updated_story = db.query(Story).filter(Story.id == story_id).first()
        timestamps = db.query(Timestamp).filter(Timestamp.story_id == story_id).all()
        
        return {
            "detail": "Story updated successfully",
            "story": {
                "id": updated_story.id,
                "title": updated_story.title,
                "desc": updated_story.desc,
                "thumbnail_url": updated_story.thumbnail_url,
                "video_url": updated_story.video_url,
                "timeline_id": updated_story.timeline_id,
                "story_date": updated_story.story_date,
                "story_type": updated_story.story_type,
                "views": updated_story.views,
                "likes": updated_story.likes,
                "created_at": updated_story.created_at
            },
            "timestamps": [
                {
                    "id": ts.id,
                    "story_id": ts.story_id,
                    "time_sec": ts.time_sec,
                    "label": ts.label
                } for ts in timestamps
            ]
        }
    except Exception as e:
        print("Error during story/timestamp update:", str(e))
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
    current_user: User = Depends(get_current_user)
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
    
    # Check if the user has already started this quiz
    quiz_attempt = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.quiz_id == quiz.id
    ).first()
    
    # If no attempt exists, create one
    if not quiz_attempt:
        quiz_attempt = QuizAttempt(
            user_id=current_user.id,
            quiz_id=quiz.id,
            completed=False
        )
        db.add(quiz_attempt)
        db.commit()
    
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
    current_user: User = Depends(get_current_user)
):
    # Check if the quiz exists
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    try:
        db.delete(quiz)
        db.commit()
        return {"detail": "Quiz deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/quiz/submit')
async def submit_quiz(
    submission: QuizSubmissionModel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if the quiz exists
    quiz = db.query(Quiz).filter(Quiz.id == submission.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Get the user's profile to update points
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Check if the user has already completed this quiz
    quiz_attempt = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.quiz_id == quiz.id
    ).first()
    
    # If the quiz has already been completed, don't award points again
    if quiz_attempt and quiz_attempt.completed:
        return {
            "message": "Quiz already completed",
            "total_questions": len(quiz.questions),
            "correct_answers": 0,
            "points_earned": 0,
            "completion_bonus": 0,
            "new_total_points": profile.points
        }
    
    try:
        # Track points and correct answers
        correct_answers = 0
        total_questions = len(quiz.questions)
        
        # Process each answer
        for answer in submission.answers:
            # Get the question
            question = db.query(Question).filter(Question.id == answer.question_id).first()
            if not question or question.quiz_id != quiz.id:
                raise HTTPException(status_code=400, detail=f"Invalid question ID: {answer.question_id}")
            
            # Check if the selected option is correct
            selected_option = db.query(Option).filter(
                Option.id == answer.selected_option_id,
                Option.question_id == answer.question_id
            ).first()
            
            if not selected_option:
                raise HTTPException(status_code=400, detail=f"Invalid option ID: {answer.selected_option_id}")
            
            # Award points for correct answers
            if selected_option.is_correct:
                correct_answers += 1
        
        # Calculate points
        correct_answer_points = correct_answers * 10  # 10 points per correct answer
        completion_bonus = 25 if len(submission.answers) == total_questions else 0  # 25 points for completing the quiz
        total_points_earned = correct_answer_points + completion_bonus
        
        # Update user's profile points
        profile.points += total_points_earned
        
        # Update or create quiz attempt record
        if not quiz_attempt:
            quiz_attempt = QuizAttempt(
                user_id=current_user.id,
                quiz_id=quiz.id,
                completed=True,
                score=total_points_earned,
                completed_at=datetime.utcnow()
            )
            db.add(quiz_attempt)
        else:
            quiz_attempt.completed = True
            quiz_attempt.score = total_points_earned
            quiz_attempt.completed_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "points_earned": total_points_earned,
            "completion_bonus": completion_bonus,
            "new_total_points": profile.points
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/user/quiz-history', response_model=list[QuizAttemptResponseModel])
async def get_user_quiz_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the quiz history for the current user"""
    quiz_attempts = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == current_user.id
    ).all()
    
    return quiz_attempts

@router.get('/user/points')
async def get_user_points(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current user's points"""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Get completed quizzes count
    completed_quizzes = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.completed == True
    ).count()
    
    return {
        "points": profile.points,
        "completed_quizzes": completed_quizzes
    }

@router.post('/story/{story_id}/like')
async def like_story(
    story_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Like or unlike a story"""
    # Check if story exists
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Check if user already liked this story
    existing_like = db.query(UserStoryLike).filter(
        UserStoryLike.user_id == current_user.id, 
        UserStoryLike.story_id == story_id
    ).first()
    
    if existing_like:
        # Unlike: remove the like record and decrement story likes
        db.delete(existing_like)
        story.likes = max(0, story.likes - 1)  # Ensure likes doesn't go below 0
        db.commit()
        return {"likes": story.likes, "liked": False}
    else:
        # Like: create new like record and increment story likes
        new_like = UserStoryLike(user_id=current_user.id, story_id=story_id)
        db.add(new_like)
        story.likes += 1
        db.commit()
        return {"likes": story.likes, "liked": True}

@router.get('/story/{story_id}/liked')
async def check_story_liked(
    story_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if the current user has liked a story"""
    # Check if story exists
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Check if user liked this story
    liked = db.query(UserStoryLike).filter(
        UserStoryLike.user_id == current_user.id, 
        UserStoryLike.story_id == story_id
    ).first() is not None
    
    return {"story_id": story_id, "likes": story.likes, "liked": liked}

@router.get('/list/characters')
async def get_characters(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a list of all characters for selection in timelines"""
    characters = db.query(Character).all()
    
    # Format response
    response = []
    for character in characters:
        character_data = {
            "id": character.id,
            "name": character.name,
            "persona": character.persona,
            "avatar_url": character.avatar_url,
            "created_at": character.created_at
        }
        response.append(character_data)
    
    return response

@router.post('/character/create', response_model=CharacterResponseModel)
async def create_character(
    name: str = Form(...),
    persona: str = Form(...),
    avatar_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Only admins can create characters
):
    """Create a new character"""
    try:
        # Validate with Pydantic
        validated_data = CharacterCreateModel(
            name=name,
            persona=persona
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    # Save avatar if provided
    avatar_url = await save_image(avatar_file) if avatar_file else None
    
    # Create character
    new_character = Character(
        name=validated_data.name,
        persona=validated_data.persona,
        avatar_url=avatar_url
    )
    
    db.add(new_character)
    try:
        db.commit()
        db.refresh(new_character)
        return new_character
    except Exception as e:
        db.rollback()
        # Delete the uploaded file if there was an error
        if avatar_url:
            delete_file(avatar_url)
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/character/{character_id}', response_model=CharacterResponseModel)
async def get_character(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get character details"""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return character

@router.patch('/character/update/{character_id}', response_model=CharacterResponseModel)
async def update_character(
    character_id: int,
    name: Optional[str] = Form(None),
    persona: Optional[str] = Form(None),
    avatar_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Only admins can update characters
):
    """Update a character"""
    # Check if character exists
    character_query = db.query(Character).filter(Character.id == character_id)
    character = character_query.first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Create update data dictionary
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if persona is not None:
        update_data["persona"] = persona
    
    # Validate with Pydantic if there's data to update
    if update_data:
        try:
            validated_data = CharacterUpdateModel(**update_data)
            update_data = {k: v for k, v in validated_data.dict().items() if v is not None}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    # Handle avatar update
    old_avatar = None
    if avatar_file:
        old_avatar = character.avatar_url
        update_data["avatar_url"] = await save_image(avatar_file)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )
    
    # Update character
    try:
        character_query.update(update_data, synchronize_session=False)
        db.commit()
        
        # Delete old avatar if it was replaced
        if old_avatar and avatar_file:
            delete_file(old_avatar)
            
        return character_query.first()
    except Exception as e:
        db.rollback()
        # Delete the new avatar if there was an error
        if avatar_file and "avatar_url" in update_data:
            delete_file(update_data["avatar_url"])
        raise HTTPException(status_code=400, detail=str(e))

@router.delete('/character/{character_id}')
async def delete_character(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Only admins can delete characters
):
    """Delete a character"""
    # Check if character exists
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Check if character is used in any timeline
    timeline_with_character = db.query(Timeline).filter(Timeline.main_character_id == character_id).first()
    if timeline_with_character:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete character that is being used in timeline: {timeline_with_character.title}"
        )
    
    # Store avatar URL for deletion after character is removed
    avatar_url = character.avatar_url
    
    # Delete character
    try:
        db.delete(character)
        db.commit()
        
        # Delete avatar if it exists
        if avatar_url:
            delete_file(avatar_url)
            
        return {"detail": "Character deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))