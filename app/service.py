from .models import Notes, select, Optional
from datetime import datetime, timezone
from sqlalchemy import or_, cast
from sqlalchemy.dialects.postgresql import JSONB
from app.config.database import redis_client, SessionDep
import json
import logging
from app.middleware import logger
# logger = logging.getLogger(__name__)

class NoteService:
    CACHE_TTL = 1800  
    def __init__(self, session: SessionDep):
        self.db = session
 

    async def create_note(self, note: Notes) -> Notes:
        try:
            stmt =  select(Notes).where(
                Notes.title == note.title,
                Notes.deleted_at.is_(None)
                )
            result = await self.db.execute(stmt)
            note_exists = result.scalar()

            if(note_exists) :
                logger.warning(
                    f"Note creation failed: Note with title because it exists  '{note.title}' "
                )
                return None
            self.db.add(note)
            await self.db.commit()
            await self.db.refresh(note)
            
            logger.info(f"Note created successfully: id={note.id}, title='{note.title}'")
            return note
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating note: {str(e)}", exc_info=True)
            raise
        
    async def get_note_by_id(self,note_id: int,user_id: str | None = None)-> Notes:
        try:
            # Check Redis cache first
            cache_key = f"note:{note_id}"
            
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for note {note_id}")
                    # Parse the cached JSON and convert back to Notes object
                    note_data = json.loads(cached)
                    return Notes(**note_data)
            except Exception as cache_error:
                logger.warning(f"Redis cache error for note {note_id}: {str(cache_error)}")
                # Continue to database if cache fails
            
            # Query database
            stmt = select(Notes).where(
                Notes.id == note_id,
                Notes.deleted_at.is_(None)
            )
            result = await self.db.execute(stmt)
            note = result.scalar()
            if not note:
                logger.info(f"Note not found: id={note_id}")
                return None
            #using user_id to allow recently viewed 
            if user_id:
               await self.add_to_recently_viewed(user_id, note_id)

            # Store in Redis cache
            try:
                # Convert SQLModel to dict for JSON serialization
                note_dict = note.model_dump(mode='json')
                await redis_client.set(
                    cache_key,
                    json.dumps(note_dict),
                    ex=self.CACHE_TTL
                )
                logger.debug(f"Cached note {note_id} in Redis")
            except Exception as cache_error:
                logger.warning(f"Failed to cache note {note_id}: {str(cache_error)}")
                # Don't fail the request if caching fails
            
            logger.info(f"Note retrieved from database: id={note_id}")
            return note
            
        except Exception as e:
            logger.error(f"Error retrieving note {note_id}: {str(e)}", exc_info=True)
            raise e

    async def get_all_notes(
        self,
        offset: int, 
        limit: int, 
        is_public: Optional[bool] = None,
        is_pinned: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        show_deleted: bool = False,
        ) -> list[Notes]: 
       
        try:
            statement = select(Notes)
            if(tags):  #e.g [politics, art, music]

                conditions = [
                    cast(Notes.tag, JSONB).contains([tag])  
                    for tag in tags
                ]
                statement = statement.where(or_(*conditions))     
                                
            if(is_public  is not None):
                statement = statement.where(Notes.is_public == is_public)
              
            if(is_pinned  is not None):
                statement = statement.where(Notes.is_pinned == is_pinned)
                
            if(not show_deleted ):
                statement = statement.where(Notes.deleted_at.is_(None))
                
            if offset is not None:
                statement = statement.offset(offset)

            if limit is not None:
                statement = statement.limit(limit)
            
            result = await self.db.execute(statement)


            notes = result.scalars().all()

            logger.info(
                f"Retrieved {len(notes)} notes with filters: "
                f" is_public={is_public}, tags={tags}, "
                f"show_deleted={show_deleted}, offset={offset}, limit={limit}"
            )
            
            return notes
        except Exception as e:
            logger.error(f"Error retrieving notes: {str(e)}", exc_info=True)
            raise e



    async def soft_delete_note(self,note_id: int ):
        try:
            note = await self.db.get(Notes, note_id)
            if not note:
                logger.warning(f"Soft delete failed: Note {note_id} not found")
                return False
            if note.deleted_at is not None:
                logger.info(f"Note {note_id} is already deleted")
                return True
            
            note.deleted_at = datetime.now()
            self.db.add(note)
            await self.db.commit()
            
            # Invalidate cache
            self._invalidate_cache(note_id)
            
            logger.info(f"Note soft deleted: id={note_id}, title='{note.title}'")
            return True    

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error soft deleting note {note_id}: {str(e)}", exc_info=True)
            raise e
        

    async def hard_delete_note(self,note_id:int):
        """
        Permanently delete a note from database
        Use with caution!
        """
        try:
            note = await self.db.get(Notes, note_id)
            if not note:
                logger.warning(f"Hard delete failed: Note {note_id} not found")
                return False
            title = note.title
            self.db.delete(note)
            await self.db.commit()
            
            #invalidate cache
            self._invalidate_cache(note_id)
            
            logger.warning(
                f"Note permanently deleted: id={note_id}, title='{title}' "
                f"(This action cannot be undone)"
            )
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error hard deleting note {note_id}: {str(e)}", exc_info=True)
            raise e
        
        
        
    async def update_note(self,note_id: int, note_update: Notes):
        try:
            note = await self.db.get(Notes, note_id)
            if not note:
                logger.warning(f"Update failed: Note {note_id} not found")
                return None
            
            note_data=note_update.model_dump(exclude_unset=True)
            note.sqlmodel_update(note_data)
            self.db.add(note)
            await self.db.commit()
            await self.db.refresh(note)
            # Update cache with new data
            self._update_cache(note)
            
            logger.info(
                f"Note updated: id={note_id}, "
                f"updated_fields={list(note_data.keys())}"
            )
                
            return note
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update note {note_id}: {str(e)}", exc_info=True)
            raise e
        
        
        
    async def restore_note(self, note_id: int) -> bool:
        """
        Restore a soft-deleted note
        """
        try:
            statement = select(Notes).where(Notes.id == note_id)
            
            note = await  self.db.execute(statement)
            note = note.scalar()
            if not note:
                logger.warning(f"Restore failed: Note {note_id} not found")
                return False
            if note.deleted_at is None:
                logger.info(f"Note {note_id} is not deleted, no restore needed")
                return False
            
            note.deleted_at = None
            self.db.add(note)
            await self.db.commit()
            # Update cache with restored note
            self._update_cache(note)
            
            logger.info(f"Note restored: id={note_id}, title={note.title}")
            return note


        except Exception as e:
            self.db.rollback()
            logger.error(f"Error restoring note {note_id}: {str(e)}", exc_info=True)
            raise e 
        
    
    async def _invalidate_cache(self, note_id: int) -> None:
        """Delete note from Redis cache"""
        try:
            cache_key = f"note:{note_id}"
            redis_client.delete(cache_key)
            logger.debug(f"Cache invalidated for note {note_id}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for note {note_id}: {str(e)}")
    
    async def _update_cache(self, note: Notes) -> None:
        """Update note in Redis cache"""
        try:
            cache_key = f"note:{note.id}"
            note_dict = note.model_dump(mode='json')
            redis_client.set(
                cache_key,
                json.dumps(note_dict),
                ex=self.CACHE_TTL
            )
            logger.debug(f"Cache updated for note {note.id}")
        except Exception as e:
            logger.warning(f"Failed to update cache for note {note.id}: {str(e)}")

    

    async def add_to_recently_viewed(self, user_id: str, note_id: int):
        """
        Add the viewed note to a Redis list for this user.
        Keeps only the last 10 viewed notes.
        """
        key = f"recent_notes:{user_id}"

        logger.info(f"[recent] Adding note_id={note_id} for user_id={user_id} (key={key})")

        try:
            removed = await redis_client.lrem(key, 0, note_id)
            logger.debug(f"[recent] Removed {removed} duplicates for note_id={note_id}")
        except Exception as e:
            logger.warning(f"[recent] Failed removing duplicate for key={key}: {str(e)}")

        try:
            pushed = await redis_client.lpush(key, note_id)
            logger.debug(f"[recent] LPUSH result (new list length) = {pushed}")
        except Exception as e:
            logger.error(f"[recent] Failed LPUSH for key={key}: {str(e)}")

        try:
            await redis_client.ltrim(key, 0, 9)
            logger.debug(f"[recent] Trimmed list to 10 items for key={key}")
        except Exception as e:
            logger.error(f"[recent] Failed LTRIM for key={key}: {str(e)}")

        logger.info(f"[recent] Successfully updated recent notes for user={user_id}")

    async def get_recently_viewed(self, user_id: str):
        """
        Returns the list of recently viewed notes (full objects, in order).
        Attempts to fetch each note from Redis cache first, falling back to DB if missing.
        """
        key = f"recent_notes:{user_id}"
        logger.info(f"[recent] Fetching recently viewed notes for user_id={user_id} (key={key})")

        note_ids = await redis_client.lrange(key, 0, -1)
        logger.debug(f"[recent] Raw Redis lrange output: {note_ids}")

        if not note_ids:
            logger.info(f"[recent] No recently viewed notes found for user {user_id}")
            return []

        # Convert Redis bytes → ints
        try:
            note_ids = [int(x) for x in note_ids]
            logger.debug(f"[recent] Parsed note IDs: {note_ids}")
        except Exception as e:
            logger.error(f"[recent] Failed converting note IDs to int: {str(e)}")
            return []

        notes = []
        missing_ids = []

        # Try fetching each note from cache
        for nid in note_ids:
            try:
                cached = await redis_client.get(f"note:{nid}")
                if cached:
                    note_obj = Notes(**json.loads(cached))
                    notes.append(note_obj)
                    logger.debug(f"[recent] Cache hit for note_id={nid}")
                else:
                    missing_ids.append(nid)
                    logger.debug(f"[recent] Cache miss for note_id={nid}")
            except Exception as e:
                logger.warning(f"[recent] Error fetching note:{nid} from cache: {str(e)}")
                missing_ids.append(nid)

        # Fetch missing notes from DB in one query
        if missing_ids:
            try:
                stmt = select(Notes).where(Notes.id.in_(missing_ids))
                result = await self.db.execute(stmt)
                db_notes = result.scalars().all()
                logger.debug(f"[recent] Fetched {len(db_notes)} missing notes from DB: {[n.id for n in db_notes]}")

                for n in db_notes:
                    notes.append(n)
                    # Update cache for next time
                    try:
                        await redis_client.set(
                            f"note:{n.id}",
                            json.dumps(n.model_dump(mode='json')),
                            ex=self.CACHE_TTL
                        )
                        logger.debug(f"[recent] Cached note_id={n.id} in Redis")
                    except Exception as e:
                        logger.warning(f"[recent] Failed to cache note_id={n.id}: {str(e)}")
            except Exception as e:
                logger.error(f"[recent] SQL fetch failed for missing_ids={missing_ids}: {str(e)}")

        # Reorder according to Redis order
        notes_map = {n.id: n for n in notes}
        ordered_notes = [notes_map[nid] for nid in note_ids if nid in notes_map]

        logger.info(f"[recent] Returning ordered notes list: {[n.id for n in ordered_notes]}")

        return ordered_notes
