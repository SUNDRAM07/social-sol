"""
Calendar service for managing calendar events and integration with PostgreSQL
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from models import CalendarEvent, Post, CalendarEventResponse
from database import get_sync_db
import logging

logger = logging.getLogger(__name__)


class CalendarService:
    """Service class for calendar event operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_event(self, event_data: Dict[str, Any]) -> Optional[CalendarEventResponse]:
        """Create a new calendar event"""
        try:
            # Extract and validate required fields
            title = event_data.get('title', '').strip()
            start_time = event_data.get('start_time')
            end_time = event_data.get('end_time')
            
            if not title:
                raise ValueError("Event title is required")
            
            if not start_time:
                raise ValueError("Start time is required")
            
            # Convert string timestamps to datetime if needed
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # Set default end time if not provided (same as start time for point-in-time events)
            if not end_time:
                end_time = start_time
            
            # Create new calendar event
            calendar_event = CalendarEvent(
                user_id=event_data.get('user_id'),  # Add user_id field
                post_id=event_data.get('post_id'),
                title=title,
                description=event_data.get('description', ''),
                start_time=start_time,
                end_time=end_time,
                all_day=event_data.get('all_day', False),
                location=event_data.get('location', ''),
                color=event_data.get('color', '#3174ad'),
                reminder_minutes=event_data.get('reminder_minutes', 15),
                recurrence_rule=event_data.get('recurrence_rule'),
                status=event_data.get('status', 'scheduled'),
                google_event_id=event_data.get('google_event_id'),
                google_event_link=event_data.get('google_event_link'),
                drive_folder_id=event_data.get('drive_folder_id'),
                drive_file_urls=event_data.get('drive_file_urls', {}),
                metadata=event_data.get('metadata', {})
            )
            
            self.db.add(calendar_event)
            self.db.commit()
            self.db.refresh(calendar_event)
            
            logger.info(f"Created calendar event: {calendar_event.id}")
            return CalendarEventResponse.from_orm(calendar_event)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create calendar event: {e}")
            raise

    def get_event(self, event_id: str) -> Optional[CalendarEventResponse]:
        """Get a calendar event by ID"""
        try:
            event = self.db.query(CalendarEvent).filter(
                CalendarEvent.id == uuid.UUID(event_id)
            ).first()
            
            if not event:
                return None
                
            return CalendarEventResponse.from_orm(event)
            
        except Exception as e:
            logger.error(f"Failed to get calendar event {event_id}: {e}")
            raise

    def get_events(self, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   status: Optional[str] = None,
                   post_id: Optional[str] = None,
                   user_id: Optional[str] = None) -> List[CalendarEventResponse]:
        """Get calendar events with optional filtering"""
        try:
            query = self.db.query(CalendarEvent)
            
            # Apply filters
            filters = []
            
            if start_date and end_date:
                filters.append(
                    or_(
                        and_(CalendarEvent.start_time >= start_date, CalendarEvent.start_time <= end_date),
                        and_(CalendarEvent.end_time >= start_date, CalendarEvent.end_time <= end_date),
                        and_(CalendarEvent.start_time <= start_date, CalendarEvent.end_time >= end_date)
                    )
                )
            elif start_date:
                filters.append(CalendarEvent.end_time >= start_date)
            elif end_date:
                filters.append(CalendarEvent.start_time <= end_date)
            
            if status:
                filters.append(CalendarEvent.status == status)
                
            if post_id:
                filters.append(CalendarEvent.post_id == uuid.UUID(post_id))
            
            if user_id:
                filters.append(CalendarEvent.user_id == uuid.UUID(user_id))
            
            if filters:
                query = query.filter(and_(*filters))
            
            events = query.order_by(CalendarEvent.start_time).all()
            return [CalendarEventResponse.from_orm(event) for event in events]
            
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            raise

    def update_event(self, event_id: str, update_data: Dict[str, Any]) -> Optional[CalendarEventResponse]:
        """Update a calendar event"""
        try:
            event = self.db.query(CalendarEvent).filter(
                CalendarEvent.id == uuid.UUID(event_id)
            ).first()
            
            if not event:
                return None
            
            # Update allowed fields
            updatable_fields = [
                'title', 'description', 'start_time', 'end_time', 'all_day',
                'location', 'color', 'reminder_minutes', 'recurrence_rule',
                'status', 'google_event_id', 'google_event_link',
                'drive_folder_id', 'drive_file_urls', 'metadata'
            ]
            
            for field, value in update_data.items():
                if field in updatable_fields and hasattr(event, field):
                    # Convert string timestamps to datetime if needed
                    if field in ['start_time', 'end_time'] and isinstance(value, str):
                        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    setattr(event, field, value)
            
            self.db.commit()
            self.db.refresh(event)
            
            logger.info(f"Updated calendar event: {event.id}")
            return CalendarEventResponse.from_orm(event)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update calendar event {event_id}: {e}")
            raise

    def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event"""
        try:
            event = self.db.query(CalendarEvent).filter(
                CalendarEvent.id == uuid.UUID(event_id)
            ).first()
            
            if not event:
                return False
            
            self.db.delete(event)
            self.db.commit()
            
            logger.info(f"Deleted calendar event: {event_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete calendar event {event_id}: {e}")
            raise

    def get_events_for_post(self, post_id: str) -> List[CalendarEventResponse]:
        """Get all calendar events associated with a specific post"""
        try:
            events = self.db.query(CalendarEvent).filter(
                CalendarEvent.post_id == uuid.UUID(post_id)
            ).order_by(CalendarEvent.start_time).all()
            
            return [CalendarEventResponse.from_orm(event) for event in events]
            
        except Exception as e:
            logger.error(f"Failed to get events for post {post_id}: {e}")
            raise

    def create_event_from_post(self, post_id: str, additional_data: Dict[str, Any] = None) -> Optional[CalendarEventResponse]:
        """Create a calendar event from an existing post"""
        try:
            post = self.db.query(Post).filter(Post.id == uuid.UUID(post_id)).first()
            if not post:
                raise ValueError(f"Post {post_id} not found")
            
            # Create event data from post - prioritize campaign name, then meaningful content
            event_title = ''
            if post.campaign_name and post.campaign_name.strip() and post.campaign_name != 'Untitled Campaign':
                event_title = post.campaign_name.strip()
            elif post.original_description and post.original_description.strip() and len(post.original_description.strip()) > 10:
                # Only use original_description if it looks like actual content (not just an ID)
                desc = post.original_description.strip()
                if not (desc.startswith('Post ') and len(desc.split('-')) > 3):  # Avoid UUID-like strings
                    event_title = f"{desc[:50]}..." if len(desc) > 50 else desc
                else:
                    event_title = "Campaign Post"
            elif post.caption and post.caption.strip():
                caption = post.caption.strip()
                event_title = f"{caption[:40]}..." if len(caption) > 40 else caption
            else:
                event_title = "Social Media Campaign"
                
            event_data = {
                'post_id': post_id,
                'title': event_title,
                'description': post.caption or post.original_description,
                'start_time': post.scheduled_at or datetime.now(),
                'status': 'scheduled' if post.status == 'scheduled' else 'draft',
                'metadata': {
                    'post_status': post.status,
                    'platforms': post.platforms,
                    'image_url': post.image_url
                }
            }
            
            # Override with additional data if provided
            if additional_data:
                event_data.update(additional_data)
            
            return self.create_event(event_data)
            
        except Exception as e:
            logger.error(f"Failed to create event from post {post_id}: {e}")
            raise

    def get_upcoming_events(self, days_ahead: int = 30) -> List[CalendarEventResponse]:
        """Get upcoming events within specified days"""
        try:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days_ahead)
            
            return self.get_events(start_date=start_date, end_date=end_date)
            
        except Exception as e:
            logger.error(f"Failed to get upcoming events: {e}")
            raise

    def sync_with_posts(self) -> Dict[str, int]:
        """Sync calendar events with existing posts that have scheduled times"""
        try:
            stats = {'created': 0, 'updated': 0, 'skipped': 0}
            
            # Get all scheduled posts
            scheduled_posts = self.db.query(Post).filter(
                and_(Post.scheduled_at.isnot(None), Post.status == 'scheduled')
            ).all()
            
            for post in scheduled_posts:
                # Check if event already exists for this post
                existing_event = self.db.query(CalendarEvent).filter(
                    CalendarEvent.post_id == post.id
                ).first()
                
                if existing_event:
                    # Update existing event
                    if existing_event.start_time != post.scheduled_at:
                        existing_event.start_time = post.scheduled_at
                        existing_event.end_time = post.scheduled_at  # Point-in-time event
                        self.db.commit()
                        stats['updated'] += 1
                    else:
                        stats['skipped'] += 1
                else:
                    # Create new event
                    self.create_event_from_post(str(post.id))
                    stats['created'] += 1
            
            logger.info(f"Sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to sync with posts: {e}")
            raise


def get_calendar_service(db: Session = None) -> CalendarService:
    """Get a calendar service instance"""
    if db is None:
        db = next(get_sync_db())
    return CalendarService(db)
