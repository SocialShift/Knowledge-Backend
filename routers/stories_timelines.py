from fastapi import APIRouter,HTTPException,Depends,status
from schemas.stories_timelines import TimelineCreateModel,StoryCreateModel,OnThisDayCreateModel,OnThisDayResponseModel,TimelineUpdateModel,StoryUpdateModel
from db.models import get_db
from sqlalchemy.orm import Session
from db.models import User, Timeline, Story, OnThisDay,Timestamp
from utils.auth import get_current_user
from fastapi.responses import JSONResponse
from datetime import date

router= APIRouter(
    prefix="/api"
)

@router.post('/otd/create')
async def create_otd(data: OnThisDayCreateModel,  db: Session= Depends(get_db), current_user: User= Depends(get_current_user)):
    print(current_user.is_admin)
    #if not current_user.is_admin:
       #raise HTTPException(detail="Only for admin", status_code=status.HTTP_401_UNAUTHORIZED)
    
    new_otd_obj= OnThisDay(
        date= data.date,
        title= data.title,
        short_desc= data.short_desc,
        image_url= data.image_url,
        story_id= data.story_id

    )
    db.add(new_otd_obj)
    try:
        db.commit()
        db.refresh(new_otd_obj)
    except Exception as e:
        db.rollback()
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
def delete_otd(id: int, db: Session = Depends(get_db)):
    otd_entry = db.query(OnThisDay).filter(OnThisDay.id == id).first()
    if not otd_entry:
        raise HTTPException(status_code=404, detail="OTD entry not found")
    db.delete(otd_entry)
    db.commit()
    return {"message": "OTD entry deleted successfully"}




@router.post("/timeline/create")
async def create_timeline(data: TimelineCreateModel, db: Session= Depends(get_db), current_user: User= Depends(get_current_user)):
    #if not current_user.is_admin:
        #raise HTTPException(detail="Only for admin", status_code=status.HTTP_401_UNAUTHORIZED)
    
    new_timeline= Timeline(
        title= data.title,
        thumbnail_url= data.thumbnail_url,
        year_range= data.year_range,
        overview= data.overview
    )
    db.add(new_timeline)
    try:
        db.commit()
        db.refresh(new_timeline)
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    
    return JSONResponse({'detail': "TimeLine Created"}, status_code=status.HTTP_201_CREATED)
    
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
    data: TimelineUpdateModel, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    timeline_query = db.query(Timeline).filter(Timeline.id == timeline_id)

    # Check if timeline exists
    timeline_obj = timeline_query.first()
    if not timeline_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Timeline Not Found"
        )
    
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED, 
    #         detail="Only for admin"
    #     )

    update_data = data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="No valid fields to update"
        )

    try:
        timeline_query.update(update_data, synchronize_session=False)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(
        {'detail': 'Timeline updated successfully'},
        status_code=status.HTTP_200_OK
    )

@router.delete("/timeline/{timeline_id}")
async def delete_timeline(timeline_id: int, db: Session= Depends(get_db), current_user: User= Depends(get_current_user)):
    timeline_obj= db.query(Timeline).filter(Timeline.id == timeline_id).first()
    if not timeline_obj:
        raise HTTPException(detail="Timeline obj not found", status_code=status.HTTP_404_NOT_FOUND)

    #if not current_user.is_admin:
        #raise HTTPException(detail="Only for admin", status_code=status.HTTP_401_UNAUTHORIZED)
    
    db.delete(timeline_obj)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    
    return JSONResponse(
        {'detail': 'Timeline deleted successfully'},
        status_code=status.HTTP_204_NO_CONTENT
    )



@router.post("/{timeline}/story/create")
async def create_story(
    timeline: int, 
    data: StoryCreateModel, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Check if the timeline exists
    current_timeline = db.query(Timeline).filter(Timeline.id == timeline).first()
    if not current_timeline:
        raise HTTPException(detail="Timeline not found", status_code=status.HTTP_404_NOT_FOUND)

    # Create Story instance (without timestamps yet)
    new_story = Story(
        title=data.title,
        desc=data.desc,
        thumbnail_url=data.thumbnail_url,
        video_url=data.video_url,
        timeline_id=current_timeline.id  # Use `id`, not object reference
    )
    db.add(new_story)
    db.commit()
    db.refresh(new_story)  # Ensure the story is committed before adding timestamps

    # Convert timestamps from Pydantic to SQLAlchemy models
    timestamp_objects = [
        Timestamp(story_id=new_story.id, time_sec=ts.time_sec, label=ts.label)
        for ts in data.timestamps
    ]

    # Add timestamps only if they exist
    if timestamp_objects:
        db.add_all(timestamp_objects)
        db.commit()

    return new_story

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
    data: StoryUpdateModel, 
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

    # if not current_user.is_admin:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Only for admin")

    update_data = data.dict(exclude_unset=True, exclude={"timestamps"})

    if update_data:
        story_query.update(update_data, synchronize_session=False)

    # Handle timestamps separately if provided
    if data.timestamps is not None:
        db.query(Timestamp).filter(Timestamp.story_id == story_id).delete()

        new_timestamps = [
            Timestamp(story_id=story_id, time_sec=ts.time_sec, label=ts.label)
            for ts in data.timestamps
        ]
        db.bulk_save_objects(new_timestamps)  # ✅ More efficient batch insert

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(
        {'detail': 'Story updated successfully'},
        status_code=status.HTTP_200_OK
    )

@router.delete("/story/delete/{story_id}")
async def delete_story(story_id: int, db: Session= Depends(get_db), current_user: User= Depends(get_current_user)):
    story_obj= db.query(Story).filter(Story.id == story_id).first()
    if not story_obj:
        raise HTTPException(detail="Story obj not found", status_code=status.HTTP_404_NOT_FOUND)

    if not current_user.is_admin:
        raise HTTPException(detail="Only for admin", status_code=status.HTTP_401_UNAUTHORIZED)
    
    db.delete(story_obj)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    
    return JSONResponse(
        {'detail': 'Story deleted successfully'},
        status_code=status.HTTP_204_NO_CONTENT
    )