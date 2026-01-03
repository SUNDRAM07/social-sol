"""
Database service functions for Social Media Agent
Provides CRUD operations and business logic for database models
Dashboard statistics functionality for monitoring post metrics
"""
import os
import re
import uuid
import json
import traceback
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from PIL import Image as PILImage
from database import db_manager, get_sync_db, database as database_connection
from image_path_utils import convert_url_to_local_path
from models import (
    Campaign, Post, Image, Caption, PostingSchedule, BatchOperation,
    PostResponse, CampaignResponse, ImageResponse, CaptionResponse,
    PostingScheduleResponse, BatchOperationResponse
)


class DatabaseService:
    """Service class for database operations"""
    
    _images_table_schema_verified: bool = False
    
    @classmethod
    async def _ensure_images_table_schema(cls):
        """Ensure images table has expected columns; add them if missing."""
        if cls._images_table_schema_verified:
            return
        
        columns = [
            ("file_name", "VARCHAR(255)"),
            ("file_size", "INTEGER"),
            ("image_width", "INTEGER"),
            ("image_height", "INTEGER"),
            ("mime_type", "VARCHAR(100)"),
            ("generation_method", "VARCHAR(100)"),
            ("generation_prompt", "TEXT"),
            ("generation_settings", "JSONB DEFAULT '{}'::jsonb")
        ]
        
        for column, column_type in columns:
            try:
                await db_manager.execute_query(
                    f"ALTER TABLE images ADD COLUMN IF NOT EXISTS {column} {column_type}"
                )
            except Exception as e:
                print(f"⚠️ Warning: Unable to ensure images.{column} column: {e}")
        
        cls._images_table_schema_verified = True
    
    @staticmethod
    def _record_to_dict(row: Any) -> Optional[Dict[str, Any]]:
        """Safely convert database Record objects to dictionaries."""
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        
        # databases.Record exposes a _mapping attribute that behaves like a dict
        mapping = getattr(row, "_mapping", None)
        if mapping is not None:
            return dict(mapping)
        
        # Fall back to items() / keys() access
        try:
            return dict(row)
        except Exception as primary_error:
            try:
                return {key: row[key] for key in row.keys()}  # type: ignore[attr-defined]
            except Exception:
                print(f"⚠️ Failed to convert record of type {type(row)} to dict: {primary_error}")
                traceback.print_exc()
                return None

    @staticmethod
    async def get_dashboard_statistics(user_id: str = None) -> Dict[str, Any]:
        """Get dashboard statistics for a user
        
        Args:
            user_id: The user ID to get statistics for
            
        Returns:
            Dictionary with dashboard statistics
        """
        async with db_manager.get_async_session() as session:
            # Get total campaigns count
            total_campaigns_query = """
                SELECT COUNT(DISTINCT COALESCE(campaign_id, batch_id)) as total
                FROM posts
                WHERE user_id = $1
            """
            total_campaigns_result = await session.fetch_one(total_campaigns_query, user_id)
            total_campaigns = total_campaigns_result['total'] if total_campaigns_result else 0
            
            # Get posts this week count
            current_date = datetime.now()
            start_of_week = current_date - timedelta(days=current_date.weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            
            posts_this_week_query = """
                SELECT COUNT(*) as total
                FROM posts
                WHERE user_id = $1
                AND created_at >= $2
            """
            posts_this_week_result = await session.fetch_one(posts_this_week_query, user_id, start_of_week)
            posts_this_week = posts_this_week_result['total'] if posts_this_week_result else 0
            
            # Get active campaigns count (with scheduled or published posts)
            active_campaigns_query = """
                SELECT COUNT(DISTINCT COALESCE(campaign_id, batch_id)) as total
                FROM posts
                WHERE user_id = $1
                AND status IN ('scheduled', 'published')
            """
            active_campaigns_result = await session.fetch_one(active_campaigns_query, user_id)
            active_campaigns = active_campaigns_result['total'] if active_campaigns_result else 0
            
            return {
                "total_campaigns": total_campaigns,
                "posts_this_week": posts_this_week,
                "active_campaigns": active_campaigns
            }
    
    @staticmethod
    async def create_post(
        campaign_name: str = None,
        original_description: str = None,
        caption: str = None,
        image_path: str = None,
        scheduled_at: datetime = None,
        campaign_id: str = None,
        platforms: List[str] = None,
        subreddit: str = None,
        status: str = None,
        batch_id: str = None,
        user_id: str = None
    ) -> str:
        """Create a new post and return its ID"""
        try:
            # Truncate caption if it's too long (database constraint workaround)
            if caption and len(caption) > 500:
                caption = caption[:497] + "..."
                # Caption truncated to 500 characters
            
            # Insert post with campaign_name (will work if column exists, ignore if not)
            try:
                # Try with campaign_name and user_id first
                query = """
                    INSERT INTO posts (id, user_id, campaign_id, campaign_name, original_description, caption, 
                                     image_path, scheduled_at, platforms, subreddit, status, batch_id)
                    VALUES (:id, :user_id, :campaign_id, :campaign_name, :description, :caption, :image_path, 
                           :scheduled_at, :platforms, :subreddit, :status, :batch_id)
                    RETURNING id
                """
                post_id = str(uuid.uuid4())
                values = {
                    "id": post_id,
                    "user_id": user_id,
                    "campaign_id": campaign_id,
                    "campaign_name": campaign_name or "",
                    "description": original_description,
                    "caption": caption,
                    "image_path": image_path,
                    "scheduled_at": scheduled_at,
                    "platforms": platforms,
                    "subreddit": subreddit,
                    "status": status or ("draft" if not scheduled_at else "scheduled"),
                    "batch_id": batch_id
                }
                await db_manager.execute_query(query, values)
                
                # Create calendar event for ALL posts (not just scheduled ones)
                if user_id:
                    from datetime import datetime, timezone
                    # Use scheduled_at if available, otherwise use current time
                    event_time = scheduled_at if scheduled_at else datetime.now(timezone.utc)
                    # Determine event status based on post status
                    event_status = status or ("draft" if not scheduled_at else "scheduled")
                    # Create meaningful title
                    event_title = campaign_name or caption[:50] if caption else original_description[:50] if original_description else "Social Media Post"
                    if len(event_title) > 50:
                        event_title = event_title[:47] + "..."
                    
                    try:
                        await DatabaseService.create_calendar_event(
                            post_id=post_id,
                            user_id=user_id,
                            title=event_title,
                            description=caption or original_description or "",
                            start_time=event_time,
                            end_time=event_time,
                            status=event_status,
                            platforms=platforms or []
                        )
                        print(f"✅ Created calendar event for post {post_id}: {event_title}")
                    except Exception as calendar_error:
                        print(f"⚠️ Warning: Failed to create calendar event for post {post_id}: {calendar_error}")
                        # Don't fail post creation if calendar event creation fails
                
                return post_id
            except Exception as e:
                if "campaign_name" in str(e):
                    # Fallback to without campaign_name but with user_id
                    # Campaign name column not found, using fallback
                    query = """
                        INSERT INTO posts (id, user_id, campaign_id, original_description, caption, 
                                         image_path, scheduled_at, platforms, subreddit, status, batch_id)
                        VALUES (:id, :user_id, :campaign_id, :description, :caption, :image_path, 
                               :scheduled_at, :platforms, :subreddit, :status, :batch_id)
                        RETURNING id
                    """
                    post_id = str(uuid.uuid4())
                    values = {
                        "id": post_id,
                        "user_id": user_id,
                        "campaign_id": campaign_id,
                        "description": original_description,
                        "caption": caption,
                        "image_path": image_path,
                        "scheduled_at": scheduled_at,
                        "platforms": platforms,
                        "subreddit": subreddit,
                        "status": status or ("draft" if not scheduled_at else "scheduled"),
                        "batch_id": batch_id
                    }
                    await db_manager.execute_query(query, values)
                    
                    # Create calendar event for ALL posts (not just scheduled ones)
                    if user_id:
                        from datetime import datetime, timezone
                        # Use scheduled_at if available, otherwise use current time
                        event_time = scheduled_at if scheduled_at else datetime.now(timezone.utc)
                        # Determine event status based on post status
                        event_status = status or ("draft" if not scheduled_at else "scheduled")
                        # Create meaningful title
                        event_title = campaign_name or caption[:50] if caption else original_description[:50] if original_description else "Social Media Post"
                        if len(event_title) > 50:
                            event_title = event_title[:47] + "..."
                        
                        try:
                            await DatabaseService.create_calendar_event(
                                post_id=post_id,
                                user_id=user_id,
                                title=event_title,
                                description=caption or original_description or "",
                                start_time=event_time,
                                end_time=event_time,
                                status=event_status,
                                platforms=platforms or []
                            )
                            print(f"✅ Created calendar event for post {post_id}: {event_title}")
                        except Exception as calendar_error:
                            print(f"⚠️ Warning: Failed to create calendar event for post {post_id}: {calendar_error}")
                            # Don't fail post creation if calendar event creation fails
                    
                    return post_id
                else:
                    raise e
            
        except Exception as e:
            print(f"Error creating post: {e}")
            raise
    
    @staticmethod
    async def save_image_info(
        post_id: str,
        file_path: str,
        generation_method: str,
        generation_prompt: str = None,
        generation_settings: Dict[str, Any] = None
    ) -> str:
        """Save image information to database"""
        try:
            await DatabaseService._ensure_images_table_schema()
            # Extract file info
            file_name = os.path.basename(file_path)
            file_size = None
            image_width = None
            image_height = None
            mime_type = None
            
            # Get file stats if file exists
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                try:
                    with PILImage.open(file_path) as img:
                        image_width, image_height = img.size
                        mime_type = f"image/{img.format.lower()}" if img.format else None
                except Exception as e:
                    print(f"Could not read image dimensions: {e}")
            
            # Insert image record (file_name stored explicitly for quick lookup)
            query = """
                INSERT INTO images (id, post_id, file_path, file_name, file_size,
                                  image_width, image_height, mime_type, generation_method,
                                  generation_prompt, generation_settings)
                VALUES (:id, :post_id, :file_path, :file_name, :file_size,
                       :image_width, :image_height, :mime_type, :generation_method,
                       :generation_prompt, :generation_settings)
                RETURNING id
            """
            
            image_id = str(uuid.uuid4())
            values = {
                "id": image_id,
                "post_id": post_id,
                "file_path": file_path,
                "file_name": file_name,
                "file_size": file_size,
                "image_width": image_width,
                "image_height": image_height,
                "mime_type": mime_type,
                "generation_method": generation_method,
                "generation_prompt": generation_prompt,
                "generation_settings": generation_settings
            }
            
            await db_manager.execute_query(query, values)
            return image_id
            
        except Exception as e:
            print(f"Error saving image info: {e}")
            raise

    @staticmethod
    def _normalize_image_records(image_records: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Normalize image records to consistent structure with URLs and metadata."""
        normalized_images: List[Dict[str, Any]] = []
        if not image_records:
            return normalized_images

        for raw_image in image_records:
            if not raw_image:
                continue

            # Ensure dictionary format
            if isinstance(raw_image, dict):
                image = raw_image
            else:
                try:
                    # Some drivers return JSON strings for aggregated objects
                    if isinstance(raw_image, str):
                        image = json.loads(raw_image)
                    else:
                        image = dict(raw_image)
                except Exception:
                    # Skip entries we can't normalize
                    continue

            # Convert UUIDs to strings
            image_id = image.get("id")
            if image_id is not None:
                image_id = str(image_id)

            # Determine file path (stored as public/filename)
            file_path = image.get("file_path") or image.get("filePath") or ""
            image_url = image.get("image_url") or image.get("url") or ""

            # Prefer converting URLs to local paths for consistency
            local_path = convert_url_to_local_path(file_path or image_url)
            if not local_path:
                # Attempt to extract filename from URL if conversion failed
                if image_url and "/public/" in image_url:
                    local_path = image_url.split("/public/")[-1]
                    local_path = f"public/{local_path}"
                elif file_path:
                    local_path = file_path.strip("/")
                else:
                    continue  # Skip invalid entries

            # Build relative and absolute URLs
            relative_url = f"/{local_path.lstrip('/')}"

            created_at = image.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            normalized_images.append({
                "id": image_id,
                "file_path": local_path,
                "image_url": relative_url,
                "file_name": image.get("file_name") or os.path.basename(local_path),
                "file_size": image.get("file_size"),
                "image_width": image.get("image_width"),
                "image_height": image.get("image_height"),
                "mime_type": image.get("mime_type"),
                "generation_method": image.get("generation_method") or image.get("method") or "user_upload",
                "generation_prompt": image.get("generation_prompt"),
                "generation_settings": image.get("generation_settings"),
                "created_at": created_at,
            })

        return normalized_images

    @staticmethod
    async def get_images_for_post(post_id: str) -> List[Dict[str, Any]]:
        """Fetch images associated with a post."""
        try:
            await DatabaseService._ensure_images_table_schema()
            query = """
                SELECT id, file_path, file_name, file_size, image_width, image_height,
                       mime_type, generation_method, generation_prompt, generation_settings,
                       created_at
                FROM images
                WHERE post_id = :post_id
                ORDER BY created_at ASC
            """
            results = await db_manager.fetch_all(query, {"post_id": post_id})
            raw_rows = [
                DatabaseService._record_to_dict(row) for row in (results or [])
            ]
            filtered_rows = [row for row in raw_rows if row]
            return DatabaseService._normalize_image_records(filtered_rows)
        except Exception as e:
            print(f"Error fetching images for post {post_id}: {e}")
            return []

    @staticmethod
    async def update_post_images(post_id: str, images_payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update images associated with a post based on payload instructions."""
        if images_payload is None:
            return await DatabaseService.get_images_for_post(post_id)

        try:
            # Normalize existing images
            existing_images = await DatabaseService.get_images_for_post(post_id)
            existing_map = {img["id"]: img for img in existing_images if img.get("id")}

            # Determine which images to keep and which to delete
            ids_to_keep = set()
            new_image_entries: List[Dict[str, Any]] = []

            for entry in images_payload:
                if not isinstance(entry, dict):
                    continue

                entry_id = entry.get("id")
                remove_flag = bool(entry.get("remove"))
                raw_path = entry.get("file_path") or entry.get("filePath")
                raw_url = entry.get("image_url") or entry.get("url")
                local_path = convert_url_to_local_path(raw_path or raw_url)

                if entry_id:
                    entry_id = str(entry_id)
                    if remove_flag:
                        # Do not keep this image
                        continue
                    # Keep existing image
                    ids_to_keep.add(entry_id)
                    # If the path changed, update the record
                    if local_path and existing_map.get(entry_id, {}).get("file_path") != local_path:
                        file_name = os.path.basename(local_path)
                        await db_manager.execute_query(
                            """
                            UPDATE images
                            SET file_path = :file_path,
                                file_name = :file_name
                            WHERE id = :id
                            """,
                            {
                                "file_path": local_path,
                                "file_name": file_name,
                                "id": entry_id,
                            },
                        )
                else:
                    if remove_flag or not local_path:
                        continue
                    new_image_entries.append({
                        "file_path": local_path,
                        "generation_method": entry.get("generation_method") or entry.get("method") or "user_upload",
                        "generation_prompt": entry.get("generation_prompt"),
                        "generation_settings": entry.get("generation_settings"),
                    })

            # Delete images not kept
            ids_existing = set(existing_map.keys())
            ids_to_delete = ids_existing - ids_to_keep
            if ids_to_delete:
                for image_id in ids_to_delete:
                    await db_manager.execute_query(
                        "DELETE FROM images WHERE id = :id",
                        {"id": image_id},
                    )

            # Insert new images
            for new_entry in new_image_entries:
                await DatabaseService.save_image_info(
                    post_id=post_id,
                    file_path=new_entry["file_path"],
                    generation_method=new_entry["generation_method"],
                    generation_prompt=new_entry.get("generation_prompt"),
                    generation_settings=new_entry.get("generation_settings"),
                )

            # Refresh image list
            final_images = await DatabaseService.get_images_for_post(post_id)

            # Update primary image on posts table
            primary_image = next((img for img in final_images if img), None)
            primary_url = primary_image.get("image_url") if primary_image else None
            primary_path = primary_image.get("file_path") if primary_image else None

            await db_manager.execute_query(
                """
                UPDATE posts
                SET image_url = :image_url,
                    image_path = :image_path,
                    updated_at = NOW()
                WHERE id = :post_id
                """,
                {
                    "image_url": primary_url,
                    "image_path": primary_path,
                    "post_id": post_id,
                },
            )

            return final_images

        except Exception as e:
            print(f"Error updating images for post {post_id}: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    @staticmethod
    async def save_caption_info(
        post_id: str,
        content: str,
        generation_method: str = "groq",
        generation_prompt: str = None,
        language: str = "en"
    ) -> str:
        """Save caption information to database"""
        try:
            # Extract hashtags from caption
            hashtags = re.findall(r'#\w+', content)
            word_count = len(content.split())
            
            query = """
                INSERT INTO captions (id, post_id, content, generation_method,
                                    generation_prompt, language, hashtags, word_count)
                VALUES (:id, :post_id, :content, :generation_method,
                       :generation_prompt, :language, :hashtags, :word_count)
                RETURNING id
            """
            
            caption_id = str(uuid.uuid4())
            values = {
                "id": caption_id,
                "post_id": post_id,
                "content": content,
                "generation_method": generation_method,
                "generation_prompt": generation_prompt,
                "language": language,
                "hashtags": hashtags,
                "word_count": word_count
            }
            
            await db_manager.execute_query(query, values)
            return caption_id
            
        except Exception as e:
            print(f"Error saving caption info: {e}")
            raise
    
    @staticmethod
    async def save_posting_schedule(
        post_id: str,
        scheduled_at: datetime,
        time_zone: str = "UTC",
        priority: int = 1,
        auto_post: bool = False
    ) -> str:
        """Save posting schedule information"""
        try:
            query = """
                INSERT INTO posting_schedules (id, post_id, scheduled_at, time_zone,
                                             priority, auto_post, status)
                VALUES (:id, :post_id, :scheduled_at, :time_zone,
                       :priority, :auto_post, :status)
                RETURNING id
            """
            
            schedule_id = str(uuid.uuid4())
            values = {
                "id": schedule_id,
                "post_id": post_id,
                "scheduled_at": scheduled_at,
                "time_zone": time_zone,
                "priority": priority,
                "auto_post": auto_post,
                "status": "pending"
            }
            
            await db_manager.execute_query(query, values)
            return schedule_id
            
        except Exception as e:
            print(f"Error saving posting schedule: {e}")
            raise
    
    @staticmethod
    async def create_batch_operation(
        description: str,
        num_posts: int,
        days_duration: int,
        created_by: str = None
    ) -> str:
        """Create a new batch operation record"""
        try:
            query = """
                INSERT INTO batch_operations (id, description, num_posts, days_duration,
                                            status, created_by)
                VALUES (:id, :description, :num_posts, :days_duration,
                       :status, :created_by)
                RETURNING id
            """
            
            batch_id = str(uuid.uuid4())
            values = {
                "id": batch_id,
                "description": description,
                "num_posts": num_posts,
                "days_duration": days_duration,
                "status": "in_progress",
                "created_by": created_by
            }
            
            await db_manager.execute_query(query, values)
            return batch_id
            
        except Exception as e:
            print(f"Error creating batch operation: {e}")
            raise
    
    @staticmethod
    async def update_batch_operation_progress(
        batch_id: str,
        posts_generated: int = None,
        posts_failed: int = None,
        status: str = None,
        error_messages: List[str] = None
    ):
        """Update batch operation progress"""
        try:
            updates = []
            values = {"batch_id": batch_id}
            
            if posts_generated is not None:
                updates.append("posts_generated = :posts_generated")
                values["posts_generated"] = posts_generated
            
            if posts_failed is not None:
                updates.append("posts_failed = :posts_failed")
                values["posts_failed"] = posts_failed
            
            if status is not None:
                updates.append("status = :status")
                values["status"] = status
                
                if status in ["completed", "failed", "cancelled"]:
                    updates.append("completed_at = NOW()")
            
            if error_messages is not None:
                updates.append("error_messages = :error_messages")
                values["error_messages"] = error_messages
            
            if updates:
                query = f"""
                    UPDATE batch_operations 
                    SET {', '.join(updates)}
                    WHERE id = :batch_id
                """
                await db_manager.execute_query(query, values)
                
        except Exception as e:
            print(f"Error updating batch operation: {e}")
            raise
    
    @staticmethod
    async def get_post_by_id(post_id: str) -> Optional[Dict[str, Any]]:
        """Get a post by ID with all related data"""
        try:
            query = """
                SELECT p.*, c.name as campaign_name
                FROM posts p
                LEFT JOIN campaigns c ON p.campaign_id = c.id
                WHERE p.id = :post_id
            """
            
            result = await db_manager.fetch_one(query, {"post_id": post_id})
            if not result:
                return None

            post = DatabaseService._record_to_dict(result)
            if not post:
                return None
            post_id_str = str(post["id"])
            post["id"] = post_id_str

            # Normalize timestamps to ISO
            if post.get("created_at"):
                post["created_at"] = post["created_at"].isoformat()
            if post.get("updated_at"):
                post["updated_at"] = post["updated_at"].isoformat()
            if post.get("scheduled_at"):
                post["scheduled_at"] = post["scheduled_at"].isoformat()
            if post.get("posted_at"):
                post["posted_at"] = post["posted_at"].isoformat()

            # Normalize primary image path
            if post.get("image_path"):
                normalized_path = convert_url_to_local_path(post["image_path"])
                post["image_path"] = normalized_path
            if post.get("image_url"):
                post["image_url"] = post["image_url"] if post["image_url"].startswith("/") else f"/{post['image_url'].lstrip('/')}"
            elif post.get("image_path"):
                post["image_url"] = f"/{post['image_path'].lstrip('/')}"

            # Attach related images/captions/schedules
            post["images"] = await DatabaseService.get_images_for_post(post_id_str)

            # Captions
            captions_query = """
                SELECT id, content, generation_method, generation_prompt,
                       language, hashtags, word_count, is_active, created_at
                FROM captions
                WHERE post_id = :post_id
                ORDER BY created_at ASC
            """
            captions = await db_manager.fetch_all(captions_query, {"post_id": post_id})
            post["captions"] = [
                row for row in (DatabaseService._record_to_dict(row) for row in (captions or []))
                if row
            ]

            # Posting schedules
            schedules_query = """
                SELECT id, scheduled_at, status, priority, time_zone
                FROM posting_schedules
                WHERE post_id = :post_id
                ORDER BY scheduled_at ASC
            """
            schedules = await db_manager.fetch_all(schedules_query, {"post_id": post_id})
            post["schedules"] = [
                row for row in (DatabaseService._record_to_dict(row) for row in (schedules or []))
                if row
            ]

            return post
            
        except Exception as e:
            print(f"Error getting post: {e}")
            return None
    
    @staticmethod
    async def get_recent_posts(limit: int = 10, user_id: str = None) -> List[Dict[str, Any]]:
        """Get recent posts with basic info, optionally filtered by user"""
        try:
            if user_id:
                query = """
                    SELECT p.id, p.original_description, p.caption, p.image_path, p.image_url,
                           p.status, p.platforms, p.scheduled_at, p.created_at, p.batch_id,
                           p.campaign_name, c.name as campaign_table_name,
                           p.engagement_metrics,
                           array_agg(DISTINCT jsonb_build_object(
                               'id', i.id,
                               'file_path', i.file_path,
                               'generation_method', i.generation_method,
                               'created_at', i.created_at
                           )) FILTER (WHERE i.id IS NOT NULL) as images
                    FROM posts p
                    LEFT JOIN campaigns c ON p.campaign_id = c.id
                    LEFT JOIN images i ON p.id = i.post_id
                    WHERE p.user_id = :user_id
                    GROUP BY p.id, c.name
                    ORDER BY p.created_at DESC
                    LIMIT :limit
                """
                results = await db_manager.fetch_all(query, {"limit": limit, "user_id": user_id})
            else:
                query = """
                    SELECT p.id, p.original_description, p.caption, p.image_path, p.image_url,
                           p.status, p.platforms, p.scheduled_at, p.created_at, p.batch_id,
                           p.campaign_name, c.name as campaign_table_name,
                           p.engagement_metrics,
                           array_agg(DISTINCT jsonb_build_object(
                               'id', i.id,
                               'file_path', i.file_path,
                               'generation_method', i.generation_method,
                               'created_at', i.created_at
                           )) FILTER (WHERE i.id IS NOT NULL) as images
                    FROM posts p
                    LEFT JOIN campaigns c ON p.campaign_id = c.id
                    LEFT JOIN images i ON p.id = i.post_id
                    GROUP BY p.id, c.name
                    ORDER BY p.created_at DESC
                    LIMIT :limit
                """
                results = await db_manager.fetch_all(query, {"limit": limit})
            posts = []
            for row in results:
                post = DatabaseService._record_to_dict(row)
                if not post:
                    continue
                post_id_str = str(post["id"])
                post["id"] = post_id_str

                # Normalize primary image paths
                if post.get("image_path"):
                    post["image_path"] = convert_url_to_local_path(post["image_path"])
                if post.get("image_url"):
                    post["image_url"] = post["image_url"] if post["image_url"].startswith("/") else f"/{post['image_url'].lstrip('/')}"
                elif post.get("image_path"):
                    post["image_url"] = f"/{post['image_path'].lstrip('/')}"

                # Normalize images collection
                post["images"] = DatabaseService._normalize_image_records(post.get("images"))

                posts.append(post)
            return posts
            
        except Exception as e:
            print(f"Error getting recent posts: {e}")
            traceback.print_exc()
            return []
    
    @staticmethod
    async def get_scheduled_posts(user_id: str = None) -> List[Dict[str, Any]]:
        """Get posts scheduled for posting, optionally filtered by user"""
        try:
            if user_id:
                query = """
                    SELECT p.id, p.original_description, p.caption, p.image_path,
                           p.scheduled_at, p.platforms, p.subreddit, p.status,
                           COALESCE(p.campaign_name, c.name, 'Untitled Campaign') as campaign_name
                    FROM posts p
                    LEFT JOIN campaigns c ON p.campaign_id = c.id
                    WHERE p.status = 'scheduled' 
                      AND p.scheduled_at IS NOT NULL
                      AND p.scheduled_at <= NOW() + INTERVAL '7 days'
                      AND p.user_id = :user_id
                    ORDER BY p.scheduled_at ASC
                """
                results = await db_manager.fetch_all(query, {"user_id": user_id})
            else:
                query = """
                    SELECT p.id, p.original_description, p.caption, p.image_path,
                           p.scheduled_at, p.platforms, p.subreddit, p.status,
                           COALESCE(p.campaign_name, c.name, 'Untitled Campaign') as campaign_name
                    FROM posts p
                    LEFT JOIN campaigns c ON p.campaign_id = c.id
                    WHERE p.status = 'scheduled' 
                      AND p.scheduled_at IS NOT NULL
                      AND p.scheduled_at <= NOW() + INTERVAL '7 days'
                    ORDER BY p.scheduled_at ASC
                """
                results = await db_manager.fetch_all(query)
            
            converted_rows = [
                DatabaseService._record_to_dict(row) for row in (results or [])
            ]
            return [row for row in converted_rows if row]
            
        except Exception as e:
            print(f"Error getting scheduled posts: {e}")
            return []
    
    @staticmethod
    async def get_batch_operation_status(batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch operation status"""
        try:
            query = """
                SELECT * FROM batch_operations WHERE id = :batch_id
            """
            
            result = await db_manager.fetch_one(query, {"batch_id": batch_id})
            return DatabaseService._record_to_dict(result)
            
        except Exception as e:
            print(f"Error getting batch operation: {e}")
            return None
    
    @staticmethod
    async def get_posts_by_batch_id(batch_id: str) -> List[Dict[str, Any]]:
        """Get all posts for a specific batch ID"""
        try:
            query = """
                SELECT p.id, p.user_id, p.original_description, p.caption, p.image_path,
                       p.status, p.platforms, p.scheduled_at, p.created_at, p.batch_id,
                       COALESCE(p.campaign_name, c.name, 'Untitled Campaign') as campaign_name
                FROM posts p
                LEFT JOIN campaigns c ON p.campaign_id = c.id
                WHERE p.batch_id = :batch_id
                ORDER BY p.created_at ASC
            """
            
            results = await db_manager.fetch_all(query, {"batch_id": batch_id})
            converted_rows = [
                DatabaseService._record_to_dict(row) for row in (results or [])
            ]
            return [row for row in converted_rows if row]
            
        except Exception as e:
            print(f"Error getting posts by batch ID: {e}")
            return []
    
    @staticmethod
    async def schedule_batch_posts(
        batch_id: str,
        platforms: List[str],
        schedule_times: List[str],
        days: int,
        user_id: str = None  # 🔧 Accept user_id parameter
    ) -> bool:
        """Schedule all posts in a batch with specified platforms and times"""
        try:
            # Get all posts in the batch
            posts = await DatabaseService.get_posts_by_batch_id(batch_id)
            
            if not posts:
                raise Exception("No posts found in batch")
            
            # Update each post with platforms and scheduled time
            for i, post in enumerate(posts):
                if i < len(schedule_times):
                    scheduled_at = schedule_times[i]
                    
                    # Update post with platforms and scheduled time
                    update_query = """
                        UPDATE posts 
                        SET platforms = :platforms, scheduled_at = :scheduled_at, status = 'scheduled'
                        WHERE id = :post_id
                    """
                    
                    await db_manager.execute_query(update_query, {
                        "platforms": platforms,
                        "scheduled_at": scheduled_at,
                        "post_id": post['id']
                    })
                    
                    # Create posting schedule record
                    await DatabaseService.save_posting_schedule(
                        post_id=post['id'],
                        scheduled_at=scheduled_at,
                        platforms=platforms
                    )
                    
                    # 🔧 FIX: Create calendar event for scheduled post
                    try:
                        # Create meaningful title from campaign name or description
                        event_title = ''
                        if post.get('campaign_name') and post['campaign_name'].strip() and post['campaign_name'] != 'Untitled Campaign':
                            event_title = post['campaign_name'].strip()
                        elif post.get('original_description') and len(post['original_description'].strip()) > 10:
                            desc = post['original_description'].strip()
                            # Avoid UUID-like strings
                            if not (desc.startswith('Post ') and len(desc.split('-')) > 3):
                                event_title = f"{desc[:50]}..." if len(desc) > 50 else desc
                            else:
                                event_title = "Campaign Post"
                        elif post.get('caption') and post['caption'].strip():
                            caption = post['caption'].strip()
                            event_title = f"{caption[:40]}..." if len(caption) > 40 else caption
                        else:
                            event_title = "Social Media Campaign"
                        
                        # Create calendar event
                        await DatabaseService.create_calendar_event(
                            post_id=post['id'],
                            user_id=user_id or post.get('user_id', '00000000-0000-0000-0000-000000000000'),  # 🔧 Use passed user_id first
                            title=event_title,
                            description=post.get('caption', '') or post.get('original_description', ''),
                            start_time=datetime.fromisoformat(scheduled_at.replace('Z', '+00:00')) if isinstance(scheduled_at, str) else scheduled_at,
                            end_time=datetime.fromisoformat(scheduled_at.replace('Z', '+00:00')) if isinstance(scheduled_at, str) else scheduled_at,
                            status='scheduled',
                            platforms=platforms
                        )
                        
                        print(f"✅ Created calendar event for post {post['id']}: {event_title}")
                        
                    except Exception as calendar_error:
                        print(f"⚠️ Warning: Failed to create calendar event for post {post['id']}: {calendar_error}")
                        # Don't fail the entire scheduling operation if calendar event creation fails
            
            return True
            
        except Exception as e:
            print(f"Error scheduling batch posts: {e}")
            return False
    
    @staticmethod
    async def get_default_campaign_id() -> Optional[str]:
        """Get the default campaign ID"""
        try:
            query = """
                SELECT id FROM campaigns 
                WHERE name = 'Default Campaign' AND is_active = true
                LIMIT 1
            """
            
            result = await db_manager.fetch_one(query)
            return str(result['id']) if result else None
            
        except Exception as e:
            print(f"Error getting default campaign: {e}")
            return None
    
    @staticmethod
    async def get_database_stats() -> Dict[str, Any]:
        """Get database statistics"""
        try:
            queries = {
                "total_posts": "SELECT COUNT(*) as count FROM posts",
                "total_images": "SELECT COUNT(*) as count FROM images",
                "total_captions": "SELECT COUNT(*) as count FROM captions",
                "pending_schedules": "SELECT COUNT(*) as count FROM posting_schedules WHERE status = 'pending'",
                "active_batches": "SELECT COUNT(*) as count FROM batch_operations WHERE status = 'in_progress'"
            }
            
            stats = {}
            for key, query in queries.items():
                result = await db_manager.fetch_one(query)
                stats[key] = result['count'] if result else 0
            
            return stats
            
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return {}


    @staticmethod
    async def get_posts_due_for_publishing() -> List[Dict[str, Any]]:
        """Get posts that are scheduled and due for publishing"""
        try:
            query = """
                SELECT id, user_id, platforms, caption, image_path, scheduled_at, original_description
                FROM posts 
                WHERE status = 'scheduled' 
                  AND scheduled_at <= NOW() 
                ORDER BY scheduled_at ASC
            """
            
            results = await db_manager.fetch_all(query)
            converted_rows = [
                DatabaseService._record_to_dict(row) for row in (results or [])
            ]
            return [row for row in converted_rows if row]
            
        except Exception as e:
            print(f"Error getting posts due for publishing: {e}")
            return []
    
    @staticmethod
    async def count_scheduled_posts() -> int:
        """Count posts that are currently scheduled"""
        try:
            query = "SELECT COUNT(*) as count FROM posts WHERE status = 'scheduled'"
            result = await db_manager.fetch_one(query)
            return result['count'] if result else 0
            
        except Exception as e:
            print(f"Error counting scheduled posts: {e}")
            return 0
    
    @staticmethod
    async def get_recent_published_posts(limit: int = 5) -> List[Dict[str, Any]]:
        """Get recently published posts"""
        try:
            query = """
                SELECT id, platforms, caption, posted_at, engagement_metrics
                FROM posts 
                WHERE status = 'published' 
                ORDER BY posted_at DESC
                LIMIT :limit
            """
            
            results = await db_manager.fetch_all(query, {"limit": limit})
            converted_rows = [
                DatabaseService._record_to_dict(row) for row in (results or [])
            ]
            return [row for row in converted_rows if row]
            
        except Exception as e:
            print(f"Error getting recent published posts: {e}")
            return []
    
    @staticmethod
    async def delete_post(post_id: str) -> bool:
        """Delete a post and all its associated data"""
        try:
            # Delete in order: schedules -> captions -> images -> post
            # This avoids foreign key constraint issues
            
            # Delete posting schedules
            await db_manager.execute_query(
                "DELETE FROM posting_schedules WHERE post_id = :post_id",
                {"post_id": post_id}
            )
            
            # Delete captions
            await db_manager.execute_query(
                "DELETE FROM captions WHERE post_id = :post_id",
                {"post_id": post_id}
            )
            
            # Get image paths before deleting (to clean up files)
            image_query = "SELECT file_path FROM images WHERE post_id = :post_id"
            image_results = await db_manager.fetch_all(image_query, {"post_id": post_id})
            
            # Delete images from database
            await db_manager.execute_query(
                "DELETE FROM images WHERE post_id = :post_id",
                {"post_id": post_id}
            )
            
            # Delete the post itself
            result = await db_manager.execute_query(
                "DELETE FROM posts WHERE id = :post_id",
                {"post_id": post_id}
            )
            
            # Clean up image files from disk
            if image_results:
                for row in image_results:
                    file_path = row['file_path']
                    if file_path and file_path.startswith('/public/'):
                        # Remove leading slash and try to delete file
                        local_path = file_path[1:]  # Remove leading slash
                        try:
                            if os.path.exists(local_path):
                                os.remove(local_path)
                                print(f"Deleted image file: {local_path}")
                        except Exception as file_error:
                            print(f"Warning: Could not delete image file {local_path}: {file_error}")
            
            print(f"Successfully deleted post {post_id} and associated data")
            return True
            
        except Exception as e:
            print(f"Error deleting post {post_id}: {e}")
            return False
    
    @staticmethod
    async def clear_all_posts() -> bool:
        """Clear all posts from the database (for testing purposes)"""
        try:
            # Delete in order: schedules -> captions -> images -> posts
            # This avoids foreign key constraint issues
            
            # Delete posting schedules
            await db_manager.execute_query("DELETE FROM posting_schedules")
            
            # Delete captions
            await db_manager.execute_query("DELETE FROM captions")
            
            # Delete images
            await db_manager.execute_query("DELETE FROM images")
            
            # Delete posts
            await db_manager.execute_query("DELETE FROM posts")
            
            print("All posts cleared from database")
            return True
            
        except Exception as e:
            print(f"Error clearing all posts: {e}")
            return False
    
    @staticmethod
    async def update_post_schedule(
        post_id: str,
        scheduled_at: datetime,
        status: str = "scheduled",
        platforms: List[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """Update a post's schedule and create calendar event if needed"""
        try:
            # Update the post
            update_query = """
                UPDATE posts 
                SET scheduled_at = :scheduled_at, status = :status, platforms = :platforms
                WHERE id = :post_id
                RETURNING id, user_id, campaign_name, original_description, caption
            """
            
            result = await db_manager.fetch_one(update_query, {
                "post_id": post_id,
                "scheduled_at": scheduled_at,
                "status": status,
                "platforms": platforms
            })
            
            if not result:
                return False
            
            # Determine which user_id to use for the calendar event
            uid_to_use = str(result['user_id']) if result['user_id'] else (user_id if user_id else None)
            
            if uid_to_use:
                # Ensure the post has a user_id for consistency going forward
                if not result['user_id'] and user_id:
                    try:
                        await db_manager.execute_query(
                            "UPDATE posts SET user_id = :user_id WHERE id = :post_id",
                            {"user_id": user_id, "post_id": post_id}
                        )
                    except Exception:
                        # Don't block scheduling if this best-effort update fails
                        pass
                
                # Check if calendar event already exists
                existing_event_query = "SELECT id FROM calendar_events WHERE post_id = :post_id"
                existing_event = await db_manager.fetch_one(existing_event_query, {"post_id": post_id})
                
                if not existing_event:
                    # Create meaningful title from campaign name or description
                    event_title = ''
                    if result['campaign_name'] and result['campaign_name'].strip():
                        event_title = result['campaign_name'].strip()
                    elif result['original_description'] and len(result['original_description'].strip()) > 10:
                        desc = result['original_description'].strip()
                        event_title = f"{desc[:50]}..." if len(desc) > 50 else desc
                    elif result['caption'] and result['caption'].strip():
                        caption = result['caption'].strip()
                        event_title = f"{caption[:40]}..." if len(caption) > 40 else caption
                    else:
                        event_title = "Social Media Post"
                    
                    await DatabaseService.create_calendar_event(
                        post_id=post_id,
                        user_id=uid_to_use,
                        title=event_title,
                        description=result['caption'] or result['original_description'] or "",
                        start_time=scheduled_at,
                        end_time=scheduled_at,
                        status=status,
                        platforms=platforms or []
                    )
                    print(f"✅ Created calendar event for post {post_id}: {event_title}")
            
            return True
            
        except Exception as e:
            print(f"Error updating post schedule: {e}")
            return False
    
    @staticmethod
    async def create_calendar_event(
        post_id: str,
        user_id: str,
        title: str,
        description: str = "",
        start_time: datetime = None,
        end_time: datetime = None,
        status: str = "scheduled",
        platforms: List[str] = None
    ) -> str:
        """Create a calendar event for a scheduled post"""
        try:
            if not start_time:
                start_time = datetime.now()
            if not end_time:
                end_time = start_time
            
            event_id = str(uuid.uuid4())
            query = """
                INSERT INTO calendar_events (id, post_id, user_id, title, description, 
                                           start_time, end_time, status, event_metadata)
                VALUES (:id, :post_id, :user_id, :title, :description, 
                       :start_time, :end_time, :status, :event_metadata)
                RETURNING id
            """
            
            values = {
                "id": event_id,
                "post_id": post_id,
                "user_id": user_id,
                "title": title,
                "description": description,
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "event_metadata": {"platforms": platforms or []}
            }
            
            # Use database connection directly to avoid db_manager issues
            try:
                await database_connection.execute(query, values)
            except Exception as e:
                # Fallback to db_manager if direct connection fails
                print(f"⚠️ Direct database execute failed, trying db_manager: {e}")
                await db_manager.execute_query(query, values)
            
            print(f"Created calendar event {event_id} for post {post_id}")
            return event_id
            
        except Exception as e:
            print(f"Error creating calendar event: {e}")
            raise
    
    @staticmethod
    async def save_social_media_account(
        user_id: str,
        platform: str,
        account_id: str,
        access_token: str,
        username: str = None,
        display_name: str = None,
        refresh_token: str = None,
        expires_at: datetime = None,
        metadata: Dict[str, Any] = None,
        scopes: List[str] = None,
        is_primary: bool = False
    ) -> bool:
        """Save or update social media account credentials in unified table"""
        try:
            import json
            
            # If setting as primary, unset other primary accounts for this platform
            if is_primary:
                await db_manager.execute_query(
                    """UPDATE social_media_accounts 
                       SET is_primary = FALSE, updated_at = NOW() 
                       WHERE user_id = :user_id AND platform = :platform""",
                    {"user_id": user_id, "platform": platform}
                )
            
            # Convert metadata to JSON string and scopes to array format
            metadata_json = json.dumps(metadata or {})
            scopes_array = scopes or []
            
            query = """
                INSERT INTO social_media_accounts 
                (user_id, platform, account_id, username, display_name, access_token, 
                 refresh_token, expires_at, metadata, scopes, is_active, is_primary)
                VALUES (:user_id, :platform, :account_id, :username, :display_name, :access_token,
                        :refresh_token, :expires_at, CAST(:metadata AS jsonb), CAST(:scopes AS text[]), TRUE, :is_primary)
                ON CONFLICT (user_id, platform, account_id) 
                DO UPDATE SET
                    username = EXCLUDED.username,
                    display_name = EXCLUDED.display_name,
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    expires_at = EXCLUDED.expires_at,
                    metadata = EXCLUDED.metadata,
                    scopes = EXCLUDED.scopes,
                    is_active = TRUE,
                    is_primary = EXCLUDED.is_primary,
                    updated_at = NOW()
            """
            
            await db_manager.execute_query(query, {
                "user_id": user_id,
                "platform": platform,
                "account_id": account_id,
                "username": username,
                "display_name": display_name,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "metadata": metadata_json,
                "scopes": scopes_array,
                "is_primary": is_primary
            })
            
            return True
            
        except Exception as e:
            print(f"Error saving {platform} account: {e}")
            return False
    
    @staticmethod
    async def disconnect_social_media_account(
        user_id: str,
        account_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Disconnect (deactivate) a social media account by ID
        
        Returns:
            tuple: (success: bool, error_message: Optional[str])
        """
        try:
            print(f"🔍 Attempting to disconnect account {account_id} for user {user_id}")
            
            # Ensure db_manager and its database are available
            if db_manager is None:
                error_msg = "db_manager is None"
                print(f"❌ {error_msg}")
                return False, error_msg
            
            if not hasattr(db_manager, 'database') or db_manager.database is None:
                error_msg = "db_manager.database is None"
                print(f"❌ {error_msg}")
                return False, error_msg
            
            if not hasattr(db_manager, 'fetch_one'):
                error_msg = "db_manager.fetch_one method not found"
                print(f"❌ {error_msg}")
                return False, error_msg
            
            # Ensure database connection is established
            try:
                # Check if database is connected using the check function
                from database import check_database_connection
                is_connected = await check_database_connection()
                if not is_connected:
                    print("⚠️ Database not connected, attempting to connect...")
                    await database_connection.connect()
            except Exception as connect_err:
                print(f"⚠️ Could not verify/establish connection: {connect_err}, trying to connect...")
                # Try to connect anyway
                try:
                    await database_connection.connect()
                except Exception as e2:
                    print(f"⚠️ Direct connect failed: {e2}, trying db_manager...")
                    try:
                        await db_manager.connect()
                    except Exception as e3:
                        print(f"⚠️ db_manager connect also failed: {e3}")
                        # Continue anyway - connection might be established
            
            # Use database connection directly (more reliable than db_manager in this context)
            # First check if account exists and belongs to user
            print(f"🔍 Calling database fetch_one directly...")
            
            try:
                # Use database connection directly to avoid db_manager issues
                existing = await database_connection.fetch_one(
                    """SELECT id, platform, display_name, username, is_active, user_id
                       FROM social_media_accounts 
                       WHERE id = :account_id""",
                    {"account_id": account_id}
                )
                print(f"🔍 fetch_one result: {existing is not None}")
            except Exception as e:
                error_msg = f"Database fetch_one error: {str(e)}"
                print(f"❌ {error_msg}")
                import traceback
                print(traceback.format_exc())
                return False, error_msg
            
            if not existing:
                error_msg = f"Account {account_id} not found in database"
                print(f"❌ {error_msg}")
                return False, error_msg
            
            # Check if account belongs to user
            existing_user_id = str(existing.get("user_id")) if existing.get("user_id") else None
            if existing_user_id != user_id:
                error_msg = f"Account {account_id} belongs to user {existing_user_id}, not {user_id}"
                print(f"❌ {error_msg}")
                return False, error_msg
            
            if not existing.get("is_active"):
                # Already disconnected - this is actually a success
                print(f"ℹ️ Account {account_id} is already disconnected")
                return True, None
            
            # Deactivate the account
            platform = existing.get('platform', 'unknown')
            print(f"🔌 Disconnecting account {account_id} (platform: {platform}, user: {user_id})")
            
            # Use database connection directly (more reliable)
            try:
                await database_connection.execute(
                    """UPDATE social_media_accounts 
                       SET is_active = FALSE, updated_at = NOW() 
                       WHERE id = :account_id AND user_id = :user_id""",
                    {"account_id": account_id, "user_id": user_id}
                )
            except Exception as e:
                error_msg = f"Database execute error: {str(e)}"
                print(f"❌ {error_msg}")
                import traceback
                print(traceback.format_exc())
                return False, error_msg
            
            # Verify the account was deactivated
            try:
                verify = await database_connection.fetch_one(
                    """SELECT is_active FROM social_media_accounts 
                       WHERE id = :account_id AND user_id = :user_id""",
                    {"account_id": account_id, "user_id": user_id}
                )
            except Exception as e:
                error_msg = f"Database verify error: {str(e)}"
                print(f"❌ {error_msg}")
                import traceback
                print(traceback.format_exc())
                return False, error_msg
            is_active_after = verify.get('is_active') if verify else None
            print(f"✅ Account {account_id} disconnected. is_active = {is_active_after}")
            
            if is_active_after is True:
                error_msg = f"Account {account_id} was not properly deactivated"
                print(f"❌ {error_msg}")
                return False, error_msg
            
            return True, None
            
        except Exception as e:
            import traceback
            error_msg = f"Error disconnecting account {account_id}: {str(e)}"
            print(f"❌ {error_msg}")
            print(traceback.format_exc())
            return False, error_msg
    
    @staticmethod
    async def get_social_media_accounts(
        user_id: str, 
        platform: str = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get social media accounts for a user, optionally filtered by platform"""
        try:
            if platform:
                query = """
                    SELECT id, platform, account_id, username, display_name, access_token,
                           refresh_token, expires_at, metadata, scopes, is_active, is_primary,
                           created_at, updated_at
                    FROM social_media_accounts
                    WHERE user_id = :user_id AND platform = :platform
                    """ + ("AND is_active = TRUE" if active_only else "") + """
                    ORDER BY is_primary DESC, created_at DESC
                """
                params = {"user_id": user_id, "platform": platform}
            else:
                query = """
                    SELECT id, platform, account_id, username, display_name, access_token,
                           refresh_token, expires_at, metadata, scopes, is_active, is_primary,
                           created_at, updated_at
                    FROM social_media_accounts
                    WHERE user_id = :user_id
                    """ + ("AND is_active = TRUE" if active_only else "") + """
                    ORDER BY platform, is_primary DESC, created_at DESC
                """
                params = {"user_id": user_id}
            
            results = await db_manager.fetch_all(query, params)
            
            accounts = []
            for row in results:
                row_dict = DatabaseService._record_to_dict(row)
                if row_dict is None:
                    continue
                import json
                # Handle metadata - could be dict or JSON string
                metadata_value = row_dict.get("metadata")
                if metadata_value:
                    if isinstance(metadata_value, dict):
                        metadata = metadata_value
                    elif isinstance(metadata_value, str):
                        try:
                            metadata = json.loads(metadata_value)
                        except:
                            metadata = {}
                    else:
                        metadata = {}
                else:
                    metadata = {}
                
                # Handle scopes - could be list or array
                scopes_list = row_dict.get("scopes") or []
                if isinstance(scopes_list, str):
                    try:
                        scopes_list = json.loads(scopes_list)
                    except:
                        scopes_list = []
                
                # Handle datetime fields - they might be datetime objects or already strings
                def format_datetime(dt_value):
                    if not dt_value:
                        return None
                    if isinstance(dt_value, str):
                        return dt_value
                    if hasattr(dt_value, 'isoformat'):
                        return dt_value.isoformat()
                    return str(dt_value)
                
                accounts.append({
                    "id": str(row_dict["id"]),
                    "platform": row_dict["platform"],
                    "account_id": row_dict["account_id"],
                    "username": row_dict.get("username"),
                    "display_name": row_dict.get("display_name"),
                    "access_token": row_dict["access_token"],
                    "refresh_token": row_dict.get("refresh_token"),
                    "expires_at": format_datetime(row_dict.get("expires_at")),
                    "metadata": metadata,
                    "scopes": scopes_list,
                    "is_active": row_dict.get("is_active", True),
                    "is_primary": row_dict.get("is_primary", False),
                    "created_at": format_datetime(row_dict.get("created_at")),
                    "updated_at": format_datetime(row_dict.get("updated_at"))
                })
            
            return accounts
            
        except Exception as e:
            print(f"Error getting social media accounts: {e}")
            return []
    
    @staticmethod
    async def get_social_media_account(
        user_id: str, 
        platform: str,
        account_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get a specific social media account (or primary account if account_id not specified)"""
        try:
            if account_id:
                query = """
                    SELECT id, platform, account_id, username, display_name, access_token,
                           refresh_token, expires_at, metadata, scopes, is_active, is_primary,
                           created_at, updated_at
                    FROM social_media_accounts
                    WHERE user_id = :user_id AND platform = :platform AND account_id = :account_id 
                    AND is_active = TRUE
                    LIMIT 1
                """
                params = {"user_id": user_id, "platform": platform, "account_id": account_id}
            else:
                # Get primary account, or first active account
                query = """
                    SELECT id, platform, account_id, username, display_name, access_token,
                           refresh_token, expires_at, metadata, scopes, is_active, is_primary,
                           created_at, updated_at
                    FROM social_media_accounts
                    WHERE user_id = :user_id AND platform = :platform AND is_active = TRUE
                    ORDER BY is_primary DESC, created_at DESC
                    LIMIT 1
                """
                params = {"user_id": user_id, "platform": platform}
            
            result = await db_manager.fetch_one(query, params)
            
            if result:
                row = DatabaseService._record_to_dict(result)
                if row is None:
                    return None
                import json
                # Handle metadata
                metadata_value = row.get("metadata")
                if metadata_value:
                    if isinstance(metadata_value, dict):
                        metadata = metadata_value
                    elif isinstance(metadata_value, str):
                        try:
                            metadata = json.loads(metadata_value)
                        except:
                            metadata = {}
                    else:
                        metadata = {}
                else:
                    metadata = {}
                
                # Handle scopes
                scopes_list = row.get("scopes") or []
                if isinstance(scopes_list, str):
                    try:
                        scopes_list = json.loads(scopes_list)
                    except:
                        scopes_list = []
                
                # Handle datetime fields - they might be datetime objects or already strings
                def format_datetime(dt_value):
                    if not dt_value:
                        return None
                    if isinstance(dt_value, str):
                        return dt_value
                    if hasattr(dt_value, 'isoformat'):
                        return dt_value.isoformat()
                    return str(dt_value)
                
                return {
                    "id": str(row["id"]),
                    "platform": row["platform"],
                    "account_id": row["account_id"],
                    "username": row.get("username"),
                    "display_name": row.get("display_name"),
                    "access_token": row["access_token"],
                    "refresh_token": row.get("refresh_token"),
                    "expires_at": format_datetime(row.get("expires_at")),
                    "metadata": metadata,
                    "scopes": scopes_list,
                    "is_active": row.get("is_active", True),
                    "is_primary": row.get("is_primary", False),
                    "created_at": format_datetime(row.get("created_at")),
                    "updated_at": format_datetime(row.get("updated_at"))
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting {platform} account: {e}")
            return None
    
    @staticmethod
    async def deactivate_social_media_account(
        user_id: str, 
        platform: str, 
        account_id: str
    ) -> bool:
        """Deactivate a social media account (soft delete)"""
        try:
            query = """
                UPDATE social_media_accounts
                SET is_active = FALSE, updated_at = NOW()
                WHERE user_id = :user_id AND platform = :platform AND account_id = :account_id
            """
            
            await db_manager.execute_query(query, {
                "user_id": user_id,
                "platform": platform,
                "account_id": account_id
            })
            
            return True
            
        except Exception as e:
            print(f"Error deactivating {platform} account: {e}")
            return False
    
    @staticmethod
    async def set_primary_account(
        user_id: str,
        platform: str,
        account_id: str
    ) -> bool:
        """Set an account as the primary account for a platform"""
        try:
            # First, unset all primary accounts for this platform
            await db_manager.execute_query(
                """UPDATE social_media_accounts 
                   SET is_primary = FALSE, updated_at = NOW() 
                   WHERE user_id = :user_id AND platform = :platform""",
                {"user_id": user_id, "platform": platform}
            )
            
            # Set the specified account as primary
            await db_manager.execute_query(
                """UPDATE social_media_accounts 
                   SET is_primary = TRUE, updated_at = NOW() 
                   WHERE user_id = :user_id AND platform = :platform AND account_id = :account_id""",
                {"user_id": user_id, "platform": platform, "account_id": account_id}
            )
            
            return True
            
        except Exception as e:
            print(f"Error setting primary account: {e}")
            return False
    
    # Legacy methods for backward compatibility (delegate to unified methods)
    @staticmethod
    async def save_instagram_account(
        user_id: str,
        instagram_account_id: str,
        access_token: str,
        instagram_username: str = None,
        facebook_page_id: str = None,
        expires_at: datetime = None,
        scopes: List[str] = None
    ) -> bool:
        """Legacy method: Save Instagram account using unified table"""
        return await DatabaseService.save_social_media_account(
            user_id=user_id,
            platform="instagram",
            account_id=instagram_account_id,
            access_token=access_token,
            username=instagram_username,
            expires_at=expires_at,
            metadata={"facebook_page_id": facebook_page_id} if facebook_page_id else {},
            scopes=scopes
        )
    
    @staticmethod
    async def get_instagram_accounts_by_user(user_id: str) -> List[Dict[str, Any]]:
        """Legacy method: Get Instagram accounts using unified table"""
        accounts = await DatabaseService.get_social_media_accounts(user_id, platform="instagram")
        # Transform to legacy format
        result = []
        for account in accounts:
            result.append({
                "id": account["id"],
                "instagram_account_id": account["account_id"],
                "instagram_username": account["username"],
                "facebook_page_id": account["metadata"].get("facebook_page_id"),
                "access_token": account["access_token"],
                "expires_at": account["expires_at"],
                "scopes": account["scopes"],
                "created_at": account["created_at"],
                "updated_at": account["updated_at"]
            })
        return result
    
    @staticmethod
    async def get_instagram_account(user_id: str, instagram_account_id: str = None) -> Optional[Dict[str, Any]]:
        """Legacy method: Get Instagram account using unified table"""
        account = await DatabaseService.get_social_media_account(user_id, "instagram", instagram_account_id)
        if account:
            return {
                "id": account["id"],
                "instagram_account_id": account["account_id"],
                "instagram_username": account["username"],
                "facebook_page_id": account["metadata"].get("facebook_page_id"),
                "access_token": account["access_token"],
                "expires_at": account["expires_at"],
                "scopes": account["scopes"],
                "created_at": account["created_at"],
                "updated_at": account["updated_at"]
            }
        return None
    
    @staticmethod
    async def deactivate_instagram_account(user_id: str, instagram_account_id: str) -> bool:
        """Legacy method: Deactivate Instagram account using unified table"""
        return await DatabaseService.deactivate_social_media_account(user_id, "instagram", instagram_account_id)


# Global service instance
db_service = DatabaseService()