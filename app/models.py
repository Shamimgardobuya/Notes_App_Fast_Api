from typing import Annotated, Optional, List
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select, Column, JSON
from sqlalchemy import DateTime, Boolean
from sqlalchemy.sql import func
import uuid

                      

class TimeStamp(SQLModel):
    created_at : datetime = Field(
                            default_factory=lambda: datetime.now(timezone.utc),
                            sa_column=Column(DateTime(timezone=True), nullable=False)
            )
    updated_at : datetime = Field(
                                sa_column=Column(
                                DateTime(timezone=True),
                                nullable=True,
                                onupdate=func.now()
        )
                                  )


class Notes(TimeStamp, table=True):
    
    __tablename__ = 'notes'
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    title: str  = Field(
        index=True,
        min_length=1,
        max_length=100,
        description = "Note title (1-100) characters "
        )
    
    content : str = Field(  
        min_length=1,
        max_length=5000,
        description="Note content (1-5000 characters)"
        )
    
    tag : Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Optional list of tags (max 30 chars each)"
        )
    
    # #public/private
    is_public: bool  = Field( default=False, index=True )
    
    # pinned 
    is_pinned: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default='0', nullable=False, index=True)
    )    
    
    #soft delete feature
    deleted_at : Optional[datetime] = Field(
        default=None,
        sa_column= Column(DateTime, nullable=True),
        description = "Note when note was deleted (NULL if not deleted)"
    )
    
    
    
