from pydantic import Field, BaseModel, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
import re
from uuid import UUID


    
class NotesResponse(BaseModel):
    id: int 
    title: str
    content: str
    tag: Optional[List[str]] = None
    is_public: bool
    is_pinned: bool
    created_at: datetime 
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
class NotesValidator(BaseModel):    
    title: str  = Field(
        min_length=1,
        max_length=100,
        description = "Note title (1-100) characters "
        )
    
    content : str = Field(  
        min_length=1,
        max_length=5000,
        description="Note content (1-5000 characters)"
        )
    
    tag : Optional[list[str]] = Field(
        default=None,
        description="Optional list of tags (max 30 chars each)"
        )
    
   
    is_public: bool  = Field(default=False)
    is_pinned: bool = Field(default=False)
    
    
   
    @field_validator("tag")
    def validate_tags(cls, v):
        if v is None:
            return v
        for tag in v:
            if len(tag) > 30:
                raise ValueError("Each tag must be at most 30 characters long.")
        return v
  
    