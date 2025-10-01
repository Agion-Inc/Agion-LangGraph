"""
Feedback API - User feedback for agent responses

Allows users to rate agent responses, which affects trust scores via the Agion SDK.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from core.database import get_db
from core.governance_client import get_governance_client
from models import ChatMessage as DBChatMessage, UserFeedback as DBUserFeedback

router = APIRouter()


class FeedbackRequest(BaseModel):
    """User feedback request model"""
    message_id: str = Field(..., description="ID of the message being rated")
    feedback_type: str = Field(..., description="thumbs_up or thumbs_down")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Optional 1-5 star rating")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional feedback comment")
    user_id: Optional[str] = Field(None, description="Optional user ID for tracking")


class FeedbackResponse(BaseModel):
    """Feedback response model"""
    status: str
    message: str
    feedback_id: str
    trust_impact: Optional[str] = None


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit user feedback for an agent response.

    Feedback is forwarded to the Agion Governance Service which applies
    the centralized trust impact algorithm. Trust scoring rules are managed
    server-side and can be updated without changing client code.

    Trust Impact (managed by governance service):
    - "Not Helpful": -2.0% trust
    - "Helpful" + 5 stars: +2.0% trust
    - "Helpful" + 4 stars: +0.5% trust
    - "Helpful" + 1-3 stars: 0% (ignored as generous ratings)
    - "Helpful" without rating: 0% (need rating for signal)
    - Star rating only (no helpful): Trust based on rating value

    See: agion-sdk-python/TRUST_SCORING_SDK_INTEGRATION_GUIDE.md

    Args:
        request: Feedback request with message_id, feedback_type, rating, comment

    Returns:
        FeedbackResponse with calculated trust impact from governance service
    """
    try:
        # Validate feedback_type
        if request.feedback_type not in ["thumbs_up", "thumbs_down"]:
            raise HTTPException(
                status_code=400,
                detail="feedback_type must be 'thumbs_up' or 'thumbs_down'"
            )

        # Get the message being rated
        result = await db.execute(
            select(DBChatMessage).where(DBChatMessage.id == request.message_id)
        )
        message = result.scalar_one_or_none()

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        if message.role != "assistant":
            raise HTTPException(
                status_code=400,
                detail="Can only provide feedback on assistant messages"
            )

        # Get execution_id from message metadata
        execution_id = None
        agent_id = message.agent_id or "unknown"

        if message.meta_data and isinstance(message.meta_data, dict):
            execution_id = message.meta_data.get("execution_id")

        if not execution_id:
            # Generate execution_id if not present (backwards compatibility)
            execution_id = f"legacy_{message.id}"

        # Determine user_id
        user_id = request.user_id or "anonymous"

        # Store feedback in local database
        feedback_id = str(uuid.uuid4())
        db_feedback = DBUserFeedback(
            id=feedback_id,
            message_id=request.message_id,
            user_id=user_id,
            feedback_type=request.feedback_type,
            rating=request.rating,
            comment=request.comment,
            created_at=datetime.utcnow()
        )
        db.add(db_feedback)
        await db.commit()

        # Submit feedback to Agion Governance Service for centralized trust scoring
        governance_client = await get_governance_client()
        full_agent_id = f"langgraph-v2:{agent_id}" if agent_id != "unknown" else "langgraph-v2:general_agent"

        # Convert thumbs_up/thumbs_down to is_helpful boolean
        is_helpful = True if request.feedback_type == "thumbs_up" else False if request.feedback_type == "thumbs_down" else None

        governance_feedback = await governance_client.submit_feedback(
            response_id=request.message_id,
            agent_id=full_agent_id,
            user_id=user_id,
            organization_id="default-org",
            conversation_id=None,  # Could extract from message metadata
            is_helpful=is_helpful,
            star_rating=request.rating,
            feedback_text=request.comment,
            feedback_category=None,
            response_metadata={
                "execution_id": execution_id,
                "agent_name": agent_id,
            },
            user_metadata={
                "source": "langgraph-ui"
            }
        )

        # Calculate trust impact message from governance response
        trust_impact = None
        if governance_feedback:
            calculated_impact = governance_feedback.get("trust_impact_calculated")
            if calculated_impact is not None:
                trust_impact = f"{calculated_impact:+.1f}% trust score (calculated by governance service)"
            else:
                trust_impact = "Feedback recorded (no trust impact)"
        else:
            # Fallback if governance service unavailable
            trust_impact = "Feedback recorded (governance service unavailable)"

        return FeedbackResponse(
            status="success",
            message="Feedback submitted successfully",
            feedback_id=feedback_id,
            trust_impact=trust_impact
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/feedback/message/{message_id}")
async def get_message_feedback(
    message_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all feedback for a specific message.

    Args:
        message_id: ID of the message

    Returns:
        List of feedback entries
    """
    try:
        result = await db.execute(
            select(DBUserFeedback)
            .where(DBUserFeedback.message_id == message_id)
            .order_by(DBUserFeedback.created_at.desc())
        )
        feedbacks = result.scalars().all()

        return {
            "status": "success",
            "message_id": message_id,
            "feedback_count": len(feedbacks),
            "feedbacks": [
                {
                    "id": f.id,
                    "feedback_type": f.feedback_type,
                    "rating": f.rating,
                    "comment": f.comment,
                    "user_id": f.user_id,
                    "created_at": f.created_at.isoformat() if f.created_at else None
                }
                for f in feedbacks
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch feedback: {str(e)}"
        )


@router.get("/feedback/stats")
async def get_feedback_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall feedback statistics.

    Returns:
        Aggregated feedback statistics
    """
    try:
        # Get all feedback
        result = await db.execute(select(DBUserFeedback))
        all_feedback = result.scalars().all()

        # Calculate statistics
        total_count = len(all_feedback)
        thumbs_up = sum(1 for f in all_feedback if f.feedback_type == "thumbs_up")
        thumbs_down = sum(1 for f in all_feedback if f.feedback_type == "thumbs_down")

        ratings = [f.rating for f in all_feedback if f.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else None

        with_comments = sum(1 for f in all_feedback if f.comment)

        return {
            "status": "success",
            "total_feedback": total_count,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "satisfaction_rate": thumbs_up / total_count if total_count > 0 else None,
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "feedback_with_comments": with_comments
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch stats: {str(e)}"
        )
