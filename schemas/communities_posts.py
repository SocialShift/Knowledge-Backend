from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID

# Community schemas
class CommunityBase(BaseModel):
    name: str
    description: Optional[str] = None
    topics: Optional[List[str]] = None

class CommunityCreate(CommunityBase):
    pass

class CommunityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    banner_url: Optional[str] = None
    icon_url: Optional[str] = None
    topics: Optional[List[str]] = None

class Community(CommunityBase):
    id: int
    banner_url: str
    icon_url: str
    created_at: datetime
    created_by: int
    
    class Config:
        from_attributes = True

class CommunityWithMemberCount(Community):
    member_count: int
    is_member: Optional[bool] = None  # Indicates if current user is a member
    
    class Config:
        from_attributes = True

# Community membership schemas
class CommunityMemberBase(BaseModel):
    user_id: int
    community_id: int

class CommunityMember(CommunityMemberBase):
    id: int
    joined_at: datetime
    
    class Config:
        from_attributes = True

class CommunityMembershipResponse(BaseModel):
    message: str
    is_member: bool

# Post schemas
class PostBase(BaseModel):
    title: str
    body: Optional[str] = None

class PostCreate(PostBase):
    community_id: int

class PostUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None

class Post(PostBase):
    id: int
    community_id: int
    upvote: int
    downvote: int
    created_at: datetime
    created_by: int
    image_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class PostWithCommunity(Post):
    community: Community
    
    class Config:
        from_attributes = True

# Comment schemas
class CommentBase(BaseModel):
    comment: str

class CommentCreate(CommentBase):
    post_id: int

class CommentUpdate(BaseModel):
    comment: Optional[str] = None

class Comment(CommentBase):
    id: int
    post_id: int
    commented_by: int
    upvote: int
    downvote: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Vote schemas
class VoteBase(BaseModel):
    vote_type: int = Field(..., description="1 for upvote, -1 for downvote")
    
    @validator('vote_type')
    def validate_vote_type(cls, v):
        if v not in [1, -1]:
            raise ValueError('vote_type must be 1 for upvote or -1 for downvote')
        return v

class PostVote(VoteBase):
    post_id: int

class CommentVote(VoteBase):
    comment_id: int
