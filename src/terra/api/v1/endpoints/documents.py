"""Document upload and management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from terra.api.deps import get_current_user, get_db
from terra.memory.db_store import DatabaseMemoryStore
from terra.models.user import User
from terra.services.documents import (
    create_document,
    delete_document,
    get_document,
    list_documents,
)

router = APIRouter()


# -- Schemas --


class DocumentUploadRequest(BaseModel):
    """Request to upload a plain-text document."""

    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=500_000)


class DocumentResponse(BaseModel):
    """Document metadata (without full content by default)."""

    id: int
    title: str
    content_hash: str
    created_at: str
    updated_at: str


class DocumentDetailResponse(BaseModel):
    """Full document including content."""

    id: int
    title: str
    content: str
    content_hash: str
    created_at: str
    updated_at: str


# -- Endpoints --


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    body: DocumentUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Upload a plain-text document."""
    memory = DatabaseMemoryStore(db)
    doc = await create_document(
        db=db,
        memory=memory,
        user_id=user.id,
        title=body.title,
        content=body.content,
    )
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        content_hash=doc.content_hash,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
    )


@router.get("/documents", response_model=list[DocumentResponse])
async def list_user_documents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """List all documents for the authenticated user."""
    docs = await list_documents(db, user.id)
    return [
        DocumentResponse(
            id=doc.id,
            title=doc.title,
            content_hash=doc.content_hash,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
        )
        for doc in docs
    ]


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_user_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Fetch a specific document with full content."""
    doc = await get_document(db, user.id, document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return DocumentDetailResponse(
        id=doc.id,
        title=doc.title,
        content=doc.content,
        content_hash=doc.content_hash,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a document."""
    deleted = await delete_document(db, user.id, document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
