"""
Chat Endpoints – AI Agent Interface
=====================================
POST /chat/message     – Send a message to the AI agent
GET  /chat/sessions    – List user's chat sessions
GET  /chat/sessions/{id} – Get session history
DELETE /chat/sessions/{id} – Delete session
"""
import secrets
from typing import List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agent import run_scholarship_agent_v2
from app.api.v1.endpoints.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.models import ChatMessage, ChatSession
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, ChatSessionResponse
from sqlalchemy import select

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/message", response_model=ChatMessageResponse)
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def send_message(
    request: Request,
    body: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Any] = None,
):
    """
    Send a message to the TamilScholar AI agent.
    Supports Tamil, English, and Tanglish input.
    Works with or without authentication (creates anonymous sessions if not logged in).
    """
    # Try to get current user if credentials provided
    try:
        if not current_user:
            # Try optional auth
            from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
            from fastapi import Header
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                from app.services.auth_service import AuthService
                auth_service = AuthService(db)
                try:
                    current_user = await auth_service.get_current_user(token)
                except:
                    current_user = None
    except:
        current_user = None

    # Get or create session
    session = None
    if body.session_id:
        # Allow anonymous sessions to resume by session token as well.
        # For authenticated users, also enforce that the session belongs to them.
        stmt = select(ChatSession).where(ChatSession.session_token == body.session_id)
        if current_user:
            stmt = stmt.where(ChatSession.user_id == current_user.id)
        else:
            stmt = stmt.where(ChatSession.user_id.is_(None))

        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

    if not session:
        session = ChatSession(
            user_id=current_user.id if current_user else None,
            session_token=secrets.token_urlsafe(32),
            messages=[],
        )
        db.add(session)
        await db.flush()

    # Build conversation history for context
    # Important: avoid lazy-loading ORM relationships in async endpoints.
    # We store conversation history directly in `ChatSession.messages` (JSONB).
    stored_messages = session.messages or []
    history = stored_messages[-8:]  # last ~4 exchanges (user+assistant)

    # Run the LangGraph agent
    agent_result = await run_scholarship_agent_v2(
        user_message=body.message,
        session_id=str(session.id),
        user_profile=current_user.profile_data or {} if current_user else {},
        conversation_history=history,
        db=db,
    )

    # Persist messages
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=body.message,
        language=agent_result.get("extra_metadata", {}).get("detected_language", "en"),
    )
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=agent_result["response"],
        language=agent_result.get("language", "en"),
        extra_metadata={
            "scholarships_surfaced": len(agent_result.get("scholarships", [])),
            "intent": str(agent_result.get("intent", "")),
            "sources": agent_result.get("sources", []),
        },
    )
    db.add(user_msg)
    db.add(assistant_msg)

    # Update session's detected language
    session.detected_language = agent_result.get("language", "en")

    # Persist lightweight conversation history for next turns.
    # Keep only the last ~20 items to avoid unbounded growth.
    session.messages = (stored_messages + [
        {"role": "user", "content": body.message},
        {"role": "assistant", "content": agent_result["response"]},
    ])[-20:]

    await db.commit()

    return ChatMessageResponse(
        session_id=session.session_token,
        response=agent_result["response"],
        language=agent_result.get("language", "en"),
        intent=str(agent_result.get("intent", "general_query")),
        scholarships=agent_result.get("scholarships", [])[:6],
        sources=agent_result.get("sources", []),
        extra_metadata=agent_result.get("extra_metadata", {}),
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all chat sessions for the current user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(20)
    )
    sessions = result.scalars().all()
    return [ChatSessionResponse.model_validate(s) for s in sessions]


@router.get("/sessions/{session_token}", response_model=ChatSessionResponse)
async def get_session(
    session_token: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a specific chat session with full history."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.session_token == session_token,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return ChatSessionResponse.model_validate(session)


@router.delete("/sessions/{session_token}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_token: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a chat session."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.session_token == session_token,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    await db.delete(session)
    await db.commit()
