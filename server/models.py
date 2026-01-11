"""
SQLAlchemy models for Social Media Agent database
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id = Column(String(255), unique=True, nullable=True)  # Nullable for email/password users
    email = Column(String(255), unique=True, nullable=True)  # Nullable for wallet-only users
    name = Column(String(255), nullable=False)
    picture_url = Column(String(500))
    password_hash = Column(String(255), nullable=True)  # For email/password authentication
    wallet_address = Column(String(44), unique=True, nullable=True)  # Solana wallet address (32-44 chars base58)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    campaigns = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    batch_operations = relationship("BatchOperation", back_populates="user", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"


class Campaign(Base):
    """Campaign model for grouping related posts"""
    __tablename__ = "campaigns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="campaigns")
    posts = relationship("Post", back_populates="campaign", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Campaign(id={self.id}, name={self.name})>"


class Post(Base):
    """Main post model for storing social media posts"""
    __tablename__ = "posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    original_description = Column(Text, nullable=False)
    caption = Column(Text)
    image_path = Column(String(500))
    image_url = Column(String(500))
    scheduled_at = Column(DateTime(timezone=True))
    posted_at = Column(DateTime(timezone=True))
    status = Column(String(50), default="draft")  # draft, scheduled, posted, failed
    platforms = Column(ARRAY(String), nullable=True)  # Array of platforms for multi-platform posting
    batch_id = Column(String(100))  # For grouping posts in batches
    engagement_metrics = Column(JSON)  # Store engagement data as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    campaign_name = Column(String(255), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="posts")
    campaign = relationship("Campaign", back_populates="posts")
    images = relationship("Image", back_populates="post", cascade="all, delete-orphan")
    captions = relationship("Caption", back_populates="post", cascade="all, delete-orphan")
    posting_schedules = relationship("PostingSchedule", back_populates="post", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Post(id={self.id}, status={self.status}, platforms={self.platforms})>"


class Image(Base):
    """Image model for storing detailed image information"""
    __tablename__ = "images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer)
    image_width = Column(Integer)
    image_height = Column(Integer)
    mime_type = Column(String(100))
    generation_method = Column(String(100))  # stability_ai, placeholder, user_upload
    generation_prompt = Column(Text)
    generation_settings = Column(JSON)  # AI generation parameters
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    post = relationship("Post", back_populates="images")
    
    def __repr__(self):
        return f"<Image(id={self.id}, file_name={self.file_name}, method={self.generation_method})>"


class Caption(Base):
    """Caption model for storing caption variations and history"""
    __tablename__ = "captions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    content = Column(Text, nullable=False)
    generation_method = Column(String(100))  # groq, manual, user_input
    generation_prompt = Column(Text)
    language = Column(String(10), default="en")
    hashtags = Column(ARRAY(String))  # Array of hashtags
    word_count = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    post = relationship("Post", back_populates="captions")
    
    def __repr__(self):
        return f"<Caption(id={self.id}, method={self.generation_method}, active={self.is_active})>"


class PostingSchedule(Base):
    """Posting schedule model for advanced scheduling features"""
    __tablename__ = "posting_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    time_zone = Column(String(50), default="UTC")
    recurring_pattern = Column(String(100))  # daily, weekly, monthly, etc.
    recurring_end_date = Column(DateTime(timezone=True))
    priority = Column(Integer, default=1)  # 1=high, 2=medium, 3=low
    auto_post = Column(Boolean, default=False)
    posted_at = Column(DateTime(timezone=True))
    status = Column(String(50), default="pending")  # pending, posted, failed, cancelled
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    post = relationship("Post", back_populates="posting_schedules")
    
    def __repr__(self):
        return f"<PostingSchedule(id={self.id}, status={self.status}, scheduled_at={self.scheduled_at})>"


class BatchOperation(Base):
    """Batch operation model for tracking bulk generation requests"""
    __tablename__ = "batch_operations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=False)
    num_posts = Column(Integer, nullable=False)
    days_duration = Column(Integer, nullable=False)
    status = Column(String(50), default="in_progress")  # in_progress, completed, failed, cancelled
    posts_generated = Column(Integer, default=0)
    posts_failed = Column(Integer, default=0)
    error_messages = Column(ARRAY(String))
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    created_by = Column(String(100))  # user identifier
    
    # Relationships
    user = relationship("User", back_populates="batch_operations")
    
    def __repr__(self):
        return f"<BatchOperation(id={self.id}, status={self.status}, posts={self.posts_generated}/{self.num_posts})>"


class CalendarEvent(Base):
    """Calendar event model for storing scheduled campaign events"""
    __tablename__ = "calendar_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    all_day = Column(Boolean, default=False)
    location = Column(String(500))
    color = Column(String(7), default="#3174ad")  # Hex color for event display
    reminder_minutes = Column(Integer, default=15)
    recurrence_rule = Column(String(200))  # RRULE format for recurring events
    status = Column(String(50), default="scheduled")  # scheduled, posted, cancelled, failed
    google_event_id = Column(String(200))  # Google Calendar event ID
    google_event_link = Column(String(500))  # Google Calendar event link
    drive_folder_id = Column(String(200))  # Associated Google Drive folder
    drive_file_urls = Column(JSON)  # URLs of associated Drive files
    event_metadata = Column(JSON)  # Additional event metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="calendar_events")
    post = relationship("Post", backref="calendar_events")
    
    def __repr__(self):
        return f"<CalendarEvent(id={self.id}, title={self.title}, status={self.status})>"


# Pydantic models for API responses
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserResponse(BaseModel):
    id: str
    google_id: Optional[str] = None  # Nullable for email/password users
    email: Optional[str] = None  # Nullable for wallet-only users
    name: str
    picture_url: Optional[str] = None
    wallet_address: Optional[str] = None  # Solana wallet address
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Convert SQLAlchemy object to Pydantic model with proper type conversion"""
        return cls(
            id=str(obj.id),
            google_id=obj.google_id,  # Can be None for email/password users
            email=obj.email,  # Can be None for wallet-only users
            name=obj.name,
            picture_url=obj.picture_url,
            wallet_address=getattr(obj, 'wallet_address', None),
            is_active=obj.is_active,
            created_at=obj.created_at,
            updated_at=obj.updated_at
        )


class CampaignResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Convert SQLAlchemy object to Pydantic model with proper type conversion"""
        return cls(
            id=str(obj.id),
            name=obj.name,
            description=obj.description,
            is_active=obj.is_active,
            created_at=obj.created_at,
            updated_at=obj.updated_at
        )


class ImageResponse(BaseModel):
    id: str
    file_path: str
    file_name: str
    file_size: Optional[int] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    mime_type: Optional[str] = None
    generation_method: Optional[str] = None
    generation_prompt: Optional[str] = None
    generation_settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CaptionResponse(BaseModel):
    id: str
    content: str
    generation_method: Optional[str] = None
    generation_prompt: Optional[str] = None
    language: str
    hashtags: Optional[List[str]] = None
    word_count: Optional[int] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class PostingScheduleResponse(BaseModel):
    id: str
    scheduled_at: datetime
    time_zone: str
    recurring_pattern: Optional[str] = None
    recurring_end_date: Optional[datetime] = None
    priority: int
    auto_post: bool
    posted_at: Optional[datetime] = None
    status: str
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PostResponse(BaseModel):
    id: str
    campaign_id: Optional[str] = None
    original_description: str
    caption: Optional[str] = None
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    status: str
    platforms: Optional[List[str]] = None  # Array of platforms for multi-platform posting
    engagement_metrics: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    # Related data
    images: List[ImageResponse] = []
    captions: List[CaptionResponse] = []
    posting_schedules: List[PostingScheduleResponse] = []
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Convert SQLAlchemy object to Pydantic model with proper type conversion"""
        return cls(
            id=str(obj.id),
            campaign_id=str(obj.campaign_id) if obj.campaign_id else None,
            original_description=obj.original_description,
            caption=obj.caption,
            image_path=obj.image_path,
            image_url=obj.image_url,
            scheduled_at=obj.scheduled_at,
            posted_at=obj.posted_at,
            status=obj.status,
            platforms=obj.platforms,
            engagement_metrics=obj.engagement_metrics,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            images=[],
            captions=[],
            posting_schedules=[]
        )


class BatchOperationResponse(BaseModel):
    id: str
    description: str
    num_posts: int
    days_duration: int
    status: str
    posts_generated: int
    posts_failed: int
    error_messages: Optional[List[str]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class CalendarEventResponse(BaseModel):
    id: str
    post_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool
    location: Optional[str] = None
    color: str
    reminder_minutes: int
    recurrence_rule: Optional[str] = None
    status: str
    google_event_id: Optional[str] = None
    google_event_link: Optional[str] = None
    drive_folder_id: Optional[str] = None
    drive_file_urls: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_orm(cls, orm_obj):
        """Custom method to handle field name differences"""
        data = {
            'id': str(orm_obj.id),
            'post_id': str(orm_obj.post_id) if orm_obj.post_id else None,
            'title': orm_obj.title,
            'description': orm_obj.description,
            'start_time': orm_obj.start_time,
            'end_time': orm_obj.end_time,
            'all_day': orm_obj.all_day,
            'location': orm_obj.location,
            'color': orm_obj.color,
            'reminder_minutes': orm_obj.reminder_minutes,
            'recurrence_rule': orm_obj.recurrence_rule,
            'status': orm_obj.status,
            'google_event_id': orm_obj.google_event_id,
            'google_event_link': orm_obj.google_event_link,
            'drive_folder_id': orm_obj.drive_folder_id,
            'drive_file_urls': orm_obj.drive_file_urls,
            'metadata': orm_obj.event_metadata,  # Map event_metadata to metadata
            'created_at': orm_obj.created_at,
            'updated_at': orm_obj.updated_at,
        }
        return cls(**data)
    
    class Config:
        from_attributes = True


class ApiUsage(Base):
    """API usage tracking model"""
    __tablename__ = "api_usage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    service = Column(String(50), nullable=False)  # 'groq', 'chatgpt', 'stability', 'piapi'
    operation = Column(String(50), nullable=False)  # 'caption', 'image', 'batch_caption'
    tokens_used = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    cost_usd = Column(String(20), default="0.0")  # Store as string to avoid precision issues
    request_data = Column(JSON)
    response_data = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'service': self.service,
            'operation': self.operation,
            'tokens_used': self.tokens_used,
            'credits_used': self.credits_used,
            'cost_usd': self.cost_usd,
            'request_data': self.request_data,
            'response_data': self.response_data,
            'created_at': self.created_at,
        }
