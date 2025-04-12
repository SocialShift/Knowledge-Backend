from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from db.models import Community, Post, Comment, User
from schemas.communities_posts import (
    Community as CommunitySchema,
    CommunityCreate, 
    CommunityUpdate,
    Post as PostSchema,
    PostCreate,
    PostUpdate,
    PostWithCommunity,
    Comment as CommentSchema,
    CommentCreate,
    CommentUpdate,
    PostVote,
    CommentVote
)
from db.models import get_db
from utils.auth import get_current_user
from utils.file_handler import save_image, delete_file

router = APIRouter(
    prefix="/api/community",
    tags=["communities"]
)

# Community endpoints
@router.post("/", response_model=CommunitySchema, status_code=status.HTTP_201_CREATED)
async def create_community(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    topics: Optional[str] = Form(None),
    banner_file: Optional[UploadFile] = File(None),
    icon_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new community"""
    # Parse topics if provided
    topics_list = None
    if topics:
        try:
            import json
            topics_list = json.loads(topics)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid topics format: {str(e)}")
    
    # Save files if provided
    banner_url = await save_image(banner_file) if banner_file else 'media/community-banners/default.jpeg'
    icon_url = await save_image(icon_file) if icon_file else 'media/community-icons/default.jpeg'
    
    db_community = Community(
        name=name,
        description=description,
        topics=topics_list,
        banner_url=banner_url,
        icon_url=icon_url,
        created_by=current_user.id
    )
    
    db.add(db_community)
    try:
        db.commit()
        db.refresh(db_community)
        return db_community
    except Exception as e:
        db.rollback()
        # Delete uploaded files if there was an error
        if banner_file:
            delete_file(banner_url)
        if icon_file:
            delete_file(icon_url)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[CommunitySchema])
def get_communities(
    skip: int = 0, 
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get all communities with pagination"""
    communities = db.query(Community).offset(skip).limit(limit).all()
    return communities

@router.get("/{community_id}", response_model=CommunitySchema)
def get_community(
    community_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific community by ID"""
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    return community

@router.put("/{community_id}", response_model=CommunitySchema)
async def update_community(
    community_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    topics: Optional[str] = Form(None),
    banner_file: Optional[UploadFile] = File(None),
    icon_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a community (only allowed for the creator or admin)"""
    db_community = db.query(Community).filter(Community.id == community_id).first()
    if not db_community:
        raise HTTPException(status_code=404, detail="Community not found")
    
    # Check if user is admin or the creator
    if not current_user.is_admin and db_community.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this community")
    
    # Update community fields
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    
    # Parse topics if provided
    if topics is not None:
        try:
            import json
            update_data["topics"] = json.loads(topics)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid topics format: {str(e)}")
    
    # Handle file updates
    old_banner = None
    old_icon = None
    
    if banner_file:
        old_banner = db_community.banner_url
        update_data["banner_url"] = await save_image(banner_file)
    
    if icon_file:
        old_icon = db_community.icon_url
        update_data["icon_url"] = await save_image(icon_file)
    
    # Update community with new data
    for key, value in update_data.items():
        setattr(db_community, key, value)
    
    try:
        db.commit()
        db.refresh(db_community)
        
        # Delete old files if they were replaced
        if old_banner and banner_file and old_banner != 'media/community-banners/default.jpeg':
            delete_file(old_banner)
        if old_icon and icon_file and old_icon != 'media/community-icons/default.jpeg':
            delete_file(old_icon)
            
        return db_community
    except Exception as e:
        db.rollback()
        # Delete new files if there was an error
        if banner_file and "banner_url" in update_data:
            delete_file(update_data["banner_url"])
        if icon_file and "icon_url" in update_data:
            delete_file(update_data["icon_url"])
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{community_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_community(
    community_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a community (only allowed for the creator or admin)"""
    db_community = db.query(Community).filter(Community.id == community_id).first()
    if not db_community:
        raise HTTPException(status_code=404, detail="Community not found")
    
    # Check if user is admin or the creator
    if not current_user.is_admin and db_community.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this community")
    
    # Store file paths before deleting
    banner_url = db_community.banner_url
    icon_url = db_community.icon_url
    
    db.delete(db_community)
    try:
        db.commit()
        
        # Delete files
        if banner_url and banner_url != 'media/community-banners/default.jpeg':
            delete_file(banner_url)
        if icon_url and icon_url != 'media/community-icons/default.jpeg':
            delete_file(icon_url)
            
        return None
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# Post endpoints
@router.post("/post/", response_model=PostSchema, status_code=status.HTTP_201_CREATED)
async def create_post(
    title: str = Form(...),
    body: Optional[str] = Form(None),
    community_id: int = Form(...),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new post in a community"""
    # Check if community exists
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    
    # Save image if provided
    image_url = None
    if image_file:
        image_url = await save_image(image_file)
    
    db_post = Post(
        title=title,
        body=body,
        community_id=community_id,
        created_by=current_user.id,
        image_url=image_url
    )
    
    db.add(db_post)
    try:
        db.commit()
        db.refresh(db_post)
        return db_post
    except Exception as e:
        db.rollback()
        # Delete uploaded file if there was an error
        if image_url:
            delete_file(image_url)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/post/", response_model=List[PostSchema])
def get_posts(
    community_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get all posts with optional filtering by community"""
    query = db.query(Post)
    if community_id:
        query = query.filter(Post.community_id == community_id)
    posts = query.order_by(Post.created_at.desc()).offset(skip).limit(limit).all()
    return posts

@router.get("/post/{post_id}", response_model=PostSchema)
def get_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific post by ID"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@router.put("/post/{post_id}", response_model=PostSchema)
async def update_post(
    post_id: int,
    title: Optional[str] = Form(None),
    body: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a post (only allowed for the creator or admin)"""
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user is admin or the creator
    if not current_user.is_admin and db_post.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this post")
    
    # Update post fields
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if body is not None:
        update_data["body"] = body
    
    # Handle image update
    old_image = None
    if image_file:
        old_image = db_post.image_url if hasattr(db_post, 'image_url') else None
        update_data["image_url"] = await save_image(image_file)
    
    # Update post with new data
    for key, value in update_data.items():
        setattr(db_post, key, value)
    
    try:
        db.commit()
        db.refresh(db_post)
        
        # Delete old image if it was replaced
        if old_image and image_file:
            delete_file(old_image)
            
        return db_post
    except Exception as e:
        db.rollback()
        # Delete new image if there was an error
        if image_file and "image_url" in update_data:
            delete_file(update_data["image_url"])
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/post/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a post (only allowed for the creator or admin)"""
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user is admin or the creator
    if not current_user.is_admin and db_post.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    # Store image path before deleting
    image_url = db_post.image_url if hasattr(db_post, 'image_url') else None
    
    db.delete(db_post)
    try:
        db.commit()
        
        # Delete image if exists
        if image_url:
            delete_file(image_url)
            
        return None
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/post/vote", status_code=status.HTTP_200_OK)
def vote_post(
    vote: PostVote,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upvote or downvote a post"""
    post = db.query(Post).filter(Post.id == vote.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if vote.vote_type == 1:
        # Upvote
        post.upvote = post.upvote + 1
    else:
        # Downvote
        post.downvote = post.downvote + 1
    
    db.commit()
    return {"message": "Vote recorded successfully"}

# Comment endpoints
@router.post("/comment/", response_model=CommentSchema, status_code=status.HTTP_201_CREATED)
def create_comment(
    comment: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new comment on a post"""
    # Check if post exists
    post = db.query(Post).filter(Post.id == comment.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    db_comment = Comment(
        comment=comment.comment,
        post_id=comment.post_id,
        commented_by=current_user.id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

@router.get("/post/{post_id}/comments", response_model=List[CommentSchema])
def get_comments(
    post_id: int,
    skip: int = 0, 
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get all comments for a specific post"""
    comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at.desc()).offset(skip).limit(limit).all()
    return comments

@router.put("/comment/{comment_id}", response_model=CommentSchema)
def update_comment(
    comment_id: int,
    comment_update: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a comment (only allowed for the creator or admin)"""
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check if user is admin or the creator
    if not current_user.is_admin and db_comment.commented_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this comment")
    
    # Update comment fields
    update_data = comment_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_comment, key, value)
    
    db.commit()
    db.refresh(db_comment)
    return db_comment

@router.delete("/comment/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a comment (only allowed for the creator or admin)"""
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check if user is admin or the creator
    if not current_user.is_admin and db_comment.commented_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    db.delete(db_comment)
    db.commit()
    return None

@router.post("/comment/vote", status_code=status.HTTP_200_OK)
def vote_comment(
    vote: CommentVote,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upvote or downvote a comment"""
    comment = db.query(Comment).filter(Comment.id == vote.comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if vote.vote_type == 1:
        # Upvote
        comment.upvote = comment.upvote + 1
    else:
        # Downvote
        comment.downvote = comment.downvote + 1
    
    db.commit()
    return {"message": "Vote recorded successfully"}
