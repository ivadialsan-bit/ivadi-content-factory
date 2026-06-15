from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    platform = Column(String(20), nullable=False)
    community_id = Column(String(20), unique=True, nullable=False)
    token = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    posts = relationship("Post", back_populates="account", cascade="all, delete-orphan")
    clips = relationship("Clip", back_populates="account", cascade="all, delete-orphan")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    theme = Column(String(100), nullable=False)
    caption = Column(Text, nullable=True)
    image_path = Column(String(200), nullable=True)
    vk_url = Column(String(300), nullable=True)
    status = Column(String(20), default="draft")
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    account = relationship("Account", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    statistics = relationship("Statistics", back_populates="post", cascade="all, delete-orphan")

class Clip(Base):
    __tablename__ = "clips"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    video_path = Column(String(200), nullable=False)
    thumbnail_path = Column(String(200), nullable=True)
    duration = Column(Integer, default=0)
    status = Column(String(20), default="draft")
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    account = relationship("Account", back_populates="clips")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    author = Column(String(100), nullable=False)
    text = Column(Text, nullable=False)
    likes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    post = relationship("Post", back_populates="comments")

class Statistics(Base):
    __tablename__ = "statistics"
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    post = relationship("Post", back_populates="statistics")

class Pattern(Base):
    __tablename__ = "patterns"
    
    id = Column(Integer, primary_key=True)
    theme = Column(String(50), nullable=False)
    heroes = Column(String(100), nullable=False)
    conclusion = Column(Text, nullable=False)
    hook = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    brand = Column(String(100), nullable=True)
    niche = Column(String(100), nullable=True)
    status = Column(String(20), default="active")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClientProject(Base):
    __tablename__ = "client_projects"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class ClientChannel(Base):
    __tablename__ = "client_channels"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("client_projects.id"), nullable=True)
    platform = Column(String(50), nullable=False)
    url = Column(String(300), nullable=True)
    status = Column(String(20), default="active")
    access_type = Column(String(50), default="manual")
    access_status = Column(String(50), default="manual_connected")
    last_sync_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClientGoal(Base):
    __tablename__ = "client_goals"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    title = Column(String(150), nullable=False)
    target_value = Column(String(100), nullable=True)
    period = Column(String(50), nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class ClientKPI(Base):
    __tablename__ = "client_kpis"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    metric = Column(String(100), nullable=False)
    value = Column(String(100), nullable=True)
    period = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClientAccountSnapshot(Base):
    __tablename__ = "client_account_snapshots"

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey("client_channels.id"), nullable=False)
    followers = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)
    views = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0)
    last_post_at = Column(DateTime, nullable=True)
    summary = Column(Text, nullable=True)
    raw_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClientProfile(Base):
    __tablename__ = "client_profiles"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, unique=True)
    positioning = Column(Text, nullable=True)
    product = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    tone_of_voice = Column(Text, nullable=True)
    content_pillars = Column(Text, nullable=True)
    usp = Column(Text, nullable=True)
    offers = Column(Text, nullable=True)
    competitors = Column(Text, nullable=True)
    pains = Column(Text, nullable=True)
    desires = Column(Text, nullable=True)
    objections = Column(Text, nullable=True)
    target_platforms = Column(Text, nullable=True)
    traffic_funnel = Column(Text, nullable=True)
    profile_status = Column(String(50), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ClientBriefFile(Base):
    __tablename__ = "client_brief_files"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    filename = Column(String(300), nullable=True)
    file_path = Column(String(500), nullable=True)
    status = Column(String(50), default="uploaded")
    parsed_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClientIntelligence(Base):
    __tablename__ = "client_intelligence"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, unique=True)
    positioning = Column(Text, nullable=True)
    audience_segments = Column(Text, nullable=True)
    tone_of_voice = Column(Text, nullable=True)
    content_pillars = Column(Text, nullable=True)
    offers = Column(Text, nullable=True)
    usp = Column(Text, nullable=True)
    pains = Column(Text, nullable=True)
    desires = Column(Text, nullable=True)
    objections = Column(Text, nullable=True)
    customer_journey = Column(Text, nullable=True)
    traffic_funnel = Column(Text, nullable=True)
    content_mix = Column(Text, nullable=True)
    platform_strategy = Column(Text, nullable=True)
    growth_hypothesis = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    status = Column(String(50), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ClientStrategy(Base):
    __tablename__ = "client_strategies"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, unique=True)
    positioning = Column(Text, nullable=True)
    content_pillars = Column(Text, nullable=True)
    platform_strategy = Column(Text, nullable=True)
    funnel = Column(Text, nullable=True)
    content_mix = Column(Text, nullable=True)
    posting_frequency = Column(Text, nullable=True)
    growth_hypotheses = Column(Text, nullable=True)
    action_plan_30 = Column(Text, nullable=True)
    risks = Column(Text, nullable=True)
    kpi_targets = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    status = Column(String(50), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class UserProfile(Base):
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True)
    skills = Column(Text, nullable=True)
    niches = Column(Text, nullable=True)
    rates = Column(Text, nullable=True)
    cases = Column(Text, nullable=True)
    about = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True)
    tg_message_id = Column(Integer, nullable=False)
    channel = Column(String(200), nullable=False)
    text = Column(Text, nullable=False)
    score = Column(Integer, default=0)
    score_reason = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    status = Column(String(50), default="new")
    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TgChannel(Base):
    __tablename__ = "tg_channels"

    id = Column(Integer, primary_key=True)
    username = Column(String(200), nullable=False, unique=True)
    title = Column(String(300), nullable=True)
    is_active = Column(Boolean, default=True)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClientContentPlan(Base):
    __tablename__ = "client_content_plans"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    month = Column(String(20), nullable=True)
    year = Column(Integer, nullable=True)
    platform_focus = Column(Text, nullable=True)
    posts_json = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    status = Column(String(50), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
