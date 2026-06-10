from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AccountCreate(BaseModel):
    name: str
    platform: str
    community_id: str
    token: str
    is_active: bool = True

class AccountResponse(BaseModel):
    id: int
    name: str
    platform: str
    community_id: str
    is_active: bool
    created_at: datetime

class PostCreate(BaseModel):
    account_id: int
    theme: str
    caption: str
    image_path: Optional[str] = None
    status: str = "draft"

class PostResponse(BaseModel):
    id: int
    account_id: int
    theme: str
    caption: str
    status: str
    views: int = 0
    likes: int = 0
    comments_count: int = 0
    published_at: Optional[datetime]
    created_at: datetime

class ClipCreate(BaseModel):
    account_id: int
    title: str
    description: Optional[str] = None
    video_path: str
    duration: int = 0
    status: str = "draft"

class ClipResponse(BaseModel):
    id: int
    account_id: int
    title: str
    description: Optional[str]
    video_path: str
    duration: int
    status: str
    views: int = 0
    likes: int = 0
    comments_count: int = 0
    published_at: Optional[datetime]
    created_at: datetime

class CommentCreate(BaseModel):
    post_id: int
    author: str
    text: str

class CommentResponse(BaseModel):
    id: int
    post_id: int
    author: str
    text: str
    likes: int = 0
    created_at: datetime

class PatternCreate(BaseModel):
    theme: str
    heroes: str
    conclusion: str
    hook: str

class PatternResponse(BaseModel):
    id: int
    theme: str
    heroes: str
    conclusion: str
    hook: str
