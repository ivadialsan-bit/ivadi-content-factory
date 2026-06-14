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

class ClientCreate(BaseModel):
    name: str
    brand: str | None = None
    niche: str | None = None
    status: str = "active"
    notes: str | None = None

class ClientUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    niche: str | None = None
    status: str | None = None
    notes: str | None = None


class ClientProjectCreate(BaseModel):
    client_id: int
    name: str
    description: str | None = None
    status: str = "active"


class ClientChannelCreate(BaseModel):
    client_id: int
    project_id: int | None = None
    platform: str
    url: str | None = None
    status: str = "active"
    access_type: str = "manual"
    access_status: str = "manual_connected"
    notes: str | None = None


class ClientGoalCreate(BaseModel):
    client_id: int
    title: str
    target_value: str | None = None
    period: str | None = None
    status: str = "active"


class ClientKPICreate(BaseModel):
    client_id: int
    metric: str
    value: str | None = None
    period: str | None = None


class ClientAccountSnapshotCreate(BaseModel):
    channel_id: int
    followers: int = 0
    posts_count: int = 0
    views: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    engagement_rate: float = 0
    summary: str | None = None
    raw_json: str | None = None


class ClientProfileCreate(BaseModel):
    client_id: int
    positioning: str | None = None
    product: str | None = None
    target_audience: str | None = None
    tone_of_voice: str | None = None
    content_pillars: str | None = None
    usp: str | None = None
    offers: str | None = None
    competitors: str | None = None
    pains: str | None = None
    desires: str | None = None
    objections: str | None = None
    target_platforms: str | None = None
    traffic_funnel: str | None = None
    profile_status: str = "draft"

class ClientProfileUpdate(BaseModel):
    positioning: str | None = None
    product: str | None = None
    target_audience: str | None = None
    tone_of_voice: str | None = None
    content_pillars: str | None = None
    usp: str | None = None
    offers: str | None = None
    competitors: str | None = None
    pains: str | None = None
    desires: str | None = None
    objections: str | None = None
    target_platforms: str | None = None
    traffic_funnel: str | None = None
    profile_status: str | None = None


class ClientIntelligenceUpdate(BaseModel):
    positioning: str | None = None
    audience_segments: str | None = None
    tone_of_voice: str | None = None
    content_pillars: str | None = None
    offers: str | None = None
    usp: str | None = None
    pains: str | None = None
    desires: str | None = None
    objections: str | None = None
    customer_journey: str | None = None
    traffic_funnel: str | None = None
    content_mix: str | None = None
    platform_strategy: str | None = None
    growth_hypothesis: str | None = None
    ai_summary: str | None = None
    status: str | None = None
