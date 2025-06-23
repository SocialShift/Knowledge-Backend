from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from db.models import Community, Post, Comment, User, CommunityMember, Report
from schemas.communities_posts import (
    Community as CommunitySchema,
    CommunityCreate, 
    CommunityUpdate,
    CommunityWithMemberCount,
    Post as PostSchema,
    PostCreate,
    PostUpdate,
    PostWithCommunity,
    Comment as CommentSchema,
    CommentCreate,
    CommentUpdate,
    PostVote,
    CommentVote,
    CommunityMember as CommunityMemberSchema,
    CommunityMembershipResponse,
    ReportCreate,
    Report as ReportSchema,
    ReportResponse,
    ReportWithDetails,
    ReportUpdate,
    ReportTypeEnum,
    ReportReasonEnum
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

@router.get("/", response_model=List[CommunityWithMemberCount])
def get_communities(
    skip: int = 0, 
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all communities with pagination, member count, and membership status"""
    communities = db.query(Community).offset(skip).limit(limit).all()
    
    result = []
    for community in communities:
        # Count members
        member_count = db.query(CommunityMember).filter(
            CommunityMember.community_id == community.id
        ).count()
        
        # Check if current user is a member
        is_member = db.query(CommunityMember).filter(
            CommunityMember.community_id == community.id,
            CommunityMember.user_id == current_user.id
        ).first() is not None
        
        # Create enhanced community object
        community_dict = {
            "id": community.id,
            "name": community.name,
            "description": community.description,
            "topics": community.topics,
            "banner_url": community.banner_url,
            "icon_url": community.icon_url,
            "created_at": community.created_at,
            "created_by": community.created_by,
            "member_count": member_count,
            "is_member": is_member
        }
        result.append(CommunityWithMemberCount(**community_dict))
    
    return result

@router.get("/{community_id}", response_model=CommunityWithMemberCount)
def get_community(
    community_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific community by ID with member count and membership status"""
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    
    # Count members
    member_count = db.query(CommunityMember).filter(
        CommunityMember.community_id == community.id
    ).count()
    
    # Check if current user is a member
    is_member = db.query(CommunityMember).filter(
        CommunityMember.community_id == community.id,
        CommunityMember.user_id == current_user.id
    ).first() is not None
    
    # Create enhanced community object
    community_dict = {
        "id": community.id,
        "name": community.name,
        "description": community.description,
        "topics": community.topics,
        "banner_url": community.banner_url,
        "icon_url": community.icon_url,
        "created_at": community.created_at,
        "created_by": community.created_by,
        "member_count": member_count,
        "is_member": is_member
    }
    
    return CommunityWithMemberCount(**community_dict)

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

# Community membership endpoints
@router.post("/{community_id}/join", response_model=CommunityMembershipResponse)
def join_community(
    community_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Join a community"""
    # Check if community exists
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    
    # Check if user is already a member
    existing_membership = db.query(CommunityMember).filter(
        CommunityMember.user_id == current_user.id,
        CommunityMember.community_id == community_id
    ).first()
    
    if existing_membership:
        return CommunityMembershipResponse(
            message="You are already a member of this community",
            is_member=True
        )
    
    # Create new membership
    new_membership = CommunityMember(
        user_id=current_user.id,
        community_id=community_id
    )
    
    db.add(new_membership)
    try:
        db.commit()
        return CommunityMembershipResponse(
            message="Successfully joined the community",
            is_member=True
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{community_id}/leave", response_model=CommunityMembershipResponse)
def leave_community(
    community_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Leave a community"""
    # Check if community exists
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    
    # Check if user is a member
    membership = db.query(CommunityMember).filter(
        CommunityMember.user_id == current_user.id,
        CommunityMember.community_id == community_id
    ).first()
    
    if not membership:
        return CommunityMembershipResponse(
            message="You are not a member of this community",
            is_member=False
        )
    
    # Remove membership
    db.delete(membership)
    try:
        db.commit()
        return CommunityMembershipResponse(
            message="Successfully left the community",
            is_member=False
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{community_id}/members", response_model=List[CommunityMemberSchema])
def get_community_members(
    community_id: int,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get all members of a community"""
    # Check if community exists
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    
    members = db.query(CommunityMember).filter(
        CommunityMember.community_id == community_id
    ).offset(skip).limit(limit).all()
    
    return members

@router.get("/{community_id}/membership-status", response_model=CommunityMembershipResponse)
def get_membership_status(
    community_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if current user is a member of the community"""
    # Check if community exists
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    
    # Check membership
    membership = db.query(CommunityMember).filter(
        CommunityMember.user_id == current_user.id,
        CommunityMember.community_id == community_id
    ).first()
    
    is_member = membership is not None
    message = "You are a member of this community" if is_member else "You are not a member of this community"
    
    return CommunityMembershipResponse(
        message=message,
        is_member=is_member
    )

@router.get("/my-communities", response_model=List[CommunitySchema])
def get_my_communities(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all communities the current user has joined"""
    # Get communities where user is a member
    member_communities = (
        db.query(Community)
        .join(CommunityMember)
        .filter(CommunityMember.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return member_communities

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

# Report endpoints
@router.post("/report", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    report: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Report a community or post"""
    
    # Validate that the reported item exists
    if report.report_type == ReportTypeEnum.COMMUNITY:
        item = db.query(Community).filter(Community.id == report.reported_item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Community not found")
    elif report.report_type == ReportTypeEnum.POST:
        item = db.query(Post).filter(Post.id == report.reported_item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user has already reported this item
    existing_report = db.query(Report).filter(
        Report.reporter_id == current_user.id,
        Report.report_type == report.report_type,
        Report.reported_item_id == report.reported_item_id
    ).first()
    
    if existing_report:
        raise HTTPException(
            status_code=400, 
            detail="You have already reported this item"
        )
    
    # Create the report
    db_report = Report(
        reporter_id=current_user.id,
        report_type=report.report_type,
        reported_item_id=report.reported_item_id,
        reason=report.reason,
        description=report.description
    )
    
    db.add(db_report)
    try:
        db.commit()
        db.refresh(db_report)
        return ReportResponse(
            message="Report submitted successfully. Thank you for helping keep our community safe.",
            report_id=db_report.id
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reports", response_model=List[ReportWithDetails])
def get_reports(
    skip: int = 0,
    limit: int = 20,
    status_filter: Optional[str] = None,
    report_type_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all reports (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = db.query(Report)
    
    # Apply filters
    if status_filter:
        query = query.filter(Report.status == status_filter)
    if report_type_filter:
        query = query.filter(Report.report_type == report_type_filter)
    
    reports = query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
    
    # Enhance reports with additional details
    enhanced_reports = []
    for report in reports:
        # Get reporter email
        reporter = db.query(User).filter(User.id == report.reporter_id).first()
        reporter_email = reporter.email if reporter else None
        
        # Get reported item title
        reported_item_title = None
        if report.report_type == ReportTypeEnum.COMMUNITY:
            community = db.query(Community).filter(Community.id == report.reported_item_id).first()
            reported_item_title = community.name if community else "Deleted Community"
        elif report.report_type == ReportTypeEnum.POST:
            post = db.query(Post).filter(Post.id == report.reported_item_id).first()
            reported_item_title = post.title if post else "Deleted Post"
        
        enhanced_report = ReportWithDetails(
            id=report.id,
            reporter_id=report.reporter_id,
            report_type=report.report_type,
            reported_item_id=report.reported_item_id,
            reason=report.reason,
            description=report.description,
            status=report.status,
            admin_notes=report.admin_notes,
            created_at=report.created_at,
            reviewed_at=report.reviewed_at,
            reviewed_by=report.reviewed_by,
            reporter_email=reporter_email,
            reported_item_title=reported_item_title
        )
        enhanced_reports.append(enhanced_report)
    
    return enhanced_reports

@router.put("/reports/{report_id}", response_model=ReportSchema)
def update_report(
    report_id: int,
    report_update: ReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a report status (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db_report = db.query(Report).filter(Report.id == report_id).first()
    if not db_report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Update report fields
    update_data = report_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_report, key, value)
    
    # Set review timestamp and reviewer
    if report_update.status and db_report.status != "pending":
        db_report.reviewed_at = datetime.utcnow
        db_report.reviewed_by = current_user.id
    
    try:
        db.commit()
        db.refresh(db_report)
        return db_report
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reports/my", response_model=List[ReportSchema])
def get_my_reports(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's submitted reports"""
    reports = (
        db.query(Report)
        .filter(Report.reporter_id == current_user.id)
        .order_by(Report.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return reports

@router.get("/reports/reasons", response_model=List[dict])
def get_report_reasons():
    """Get all available report reasons"""
    reasons = []
    for reason in ReportReasonEnum:
        # Convert enum values to human-readable format
        readable_reason = reason.value.replace('_', ' ').title()
        reasons.append({
            "value": reason.value,
            "label": readable_reason
        })
    return reasons

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
