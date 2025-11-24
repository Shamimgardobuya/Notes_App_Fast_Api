from fastapi import APIRouter, Depends, status, Query, HTTPException
from typing import Optional, List
from uuid import UUID
from app.config.database import SessionDep
from app.models import  Notes
from app.validators import NotesValidator, NotesResponse
from app.service import NoteService
from fastapi_limiter.depends import RateLimiter

router = APIRouter()


@router.post(
    '/',
    status_code=status.HTTP_201_CREATED,
    response_model=NotesResponse,
    dependencies=[Depends(RateLimiter(100, seconds=600))],
    description=
    """creates notes

    Example payload:
        title="Welcome to Notes API",
        content="This is a sample public note. Everyone can see this!",
        tag=["welcome", "public"],
        is_public=True,
        is_pinned=True
    
    """
)
async def create_notes(data: NotesValidator, session: SessionDep):
    note_session = NoteService(session)
    db_note = Notes(**data.model_dump())
    note = await note_session.create_note(note=db_note)
    if note:
        return NotesResponse.model_validate(note)
    raise HTTPException(status_code=400, detail="Note already exists")

@router.get("/recent", 
            status_code=status.HTTP_200_OK,
            summary="Get recently viewed notes",
            description="""
        Return the list of recently viewed notes for a given user.

        - The list is **ordered by most recent first**.  
        - The number of notes tracked in Redis is limited (default: 10).  
        - The `user_id` parameter is required to identify which user's history to return.  
        - Notes that have been deleted (soft delete) are automatically excluded.
        """
            )

async def get_recent_notes(
    session: SessionDep,
    user_id: str = Query(None, description=
       "Unique identifier of the user whose recently viewed notes "
        "are being retrieved. This is the same ID used when viewing notes."                         
        
        ),
    
    
):
    service = NoteService(session)
    return await service.get_recently_viewed(user_id)



@router.get(
    '/{note_id}',
    status_code=status.HTTP_200_OK,
    response_model=NotesResponse,
    dependencies=[Depends(RateLimiter(100, seconds=600))],
    description= 
    """
    Get a note by ID, excluding soft-deleted notes
    
        
    This endpoint also **records the note as recently viewed** for the user specified by `user_id`.  
    The `user_id` is required to track recently viewed notes in Redis.  
    It **does not** affect the note itself and is **not stored in the database**.  
    It should be a unique identifier per user (string, UUID, or numeric ID depending on your system).  

    """

)

async def get_note(
    note_id: int, 
    session: SessionDep, 
    user_id: str = Query(None, description=
                         """
        "Unique identifier of the user viewing the note. "
        "Used to track recently viewed notes. "
        "This is required for maintaining a per-user history in Redis, "
        "and is NOT stored in the Notes database."   
        "example user_id : an12"                      
                         """)):

    note_session = NoteService(session)
    note = await note_session.get_note_by_id(note_id, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
     # Track recently viewed only if user_id provided
    if user_id:
        await note_session.add_to_recently_viewed(user_id=user_id, note_id=note_id)
    return NotesResponse.model_validate(note)

@router.put(
    '/{note_id}',
    status_code=status.HTTP_200_OK,
    response_model=NotesResponse,
    dependencies=[Depends(RateLimiter(100, seconds=600))],
    description=  """Update a note by ID, excluding soft-deleted note"""

)
async def update_note(note_id: int, notes: NotesValidator, session: SessionDep):

    note_session = NoteService(session)
    db_note = Notes(**notes.model_dump())
    updated_note = await note_session.update_note(note_id, db_note)
    if not updated_note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NotesResponse.model_validate(updated_note)


@router.get(
    '/',
    status_code=status.HTTP_200_OK,
    response_model=List[NotesResponse],
    dependencies=[Depends(RateLimiter(100, seconds=600))],
    description=
    """
        Get notes with optional filters
        
        Args:
            is_public: Filter by public/private
            tags: Filter by tags (notes must have at least one matching tag)
            show_deleted: Include soft-deleted notes
            offset: Number of records to skip
            limit: Maximum number of records to return
    """
)
async def get_all_notes(
    session: SessionDep,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
    tags: Optional[List[str]] = Query(None),
    is_public: Optional[bool] = None,
    is_pinned: Optional[bool] = None,
    show_deleted: Optional[bool] = None
):
    
    note_session = NoteService(session)
    notes = await note_session.get_all_notes(
        offset=offset,
        limit=limit,
        tags=tags,
        is_public=is_public,
        is_pinned=is_pinned,
        show_deleted=show_deleted
    )
    return [NotesResponse.model_validate(note) for note in notes]


@router.delete(
    '/softdelete/{note_id}',
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimiter(100, seconds=600))],
    description=
    """
        Soft delete a note by setting deleted_at timestamp
        Returns True if deleted, False if not found
    """
)
async def soft_delete_note(note_id: int, session: SessionDep):
    
    note_session = NoteService(session)
    success = await note_session.soft_delete_note(note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"success": True, "message": "Note soft-deleted successfully"}


@router.delete(
    '/{note_id}',
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimiter(100, seconds=600))],
    description="""
    Permanently delete a note from database
  
    """
)
async def hard_delete_note(note_id: int, session: SessionDep):
    
    note_session = NoteService(session)
    success = await note_session.hard_delete_note(note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"success": True, "message": "Note permanently deleted"}


@router.post(
    '/restore/{note_id}',
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimiter(100, seconds=600))]
)
async def restore_deleted_note(note_id: int, session: SessionDep):
    """
    Restore a soft-deleted note
    """
    note_session = NoteService(session)
    restored_note = await note_session.restore_note(note_id)
    if not restored_note:
        raise HTTPException(status_code=404, detail="Note not found or not deleted")
    return NotesResponse.model_validate(restored_note)
