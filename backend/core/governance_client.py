"""
Governance Service HTTP Client
Handles communication with the Agion Governance Service for trust scoring and feedback
"""

import logging
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime
from core.config import settings

logger = logging.getLogger(__name__)


class GovernanceClient:
    """
    HTTP client for Agion Governance Service.

    Implements the Trust Scoring & Human Feedback API as per:
    TRUST_SCORING_SDK_INTEGRATION_GUIDE.md
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize governance client.

        Args:
            base_url: Base URL of governance service (defaults to agion_gateway_url)
        """
        self.base_url = base_url or settings.agion_gateway_url
        self.api_base = f"{self.base_url}/api/v1"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def submit_feedback(
        self,
        response_id: str,
        agent_id: str,
        user_id: str,
        organization_id: str = "default-org",
        conversation_id: Optional[str] = None,
        is_helpful: Optional[bool] = None,
        star_rating: Optional[int] = None,
        feedback_text: Optional[str] = None,
        feedback_category: Optional[str] = None,
        response_metadata: Optional[Dict[str, Any]] = None,
        user_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Submit user feedback to governance service.

        The governance service will:
        1. Apply centralized trust impact algorithm
        2. Create trust event
        3. Update agent trust score
        4. Return calculated trust impact

        Args:
            response_id: ID of the agent response being rated
            agent_id: ID of the agent
            user_id: ID of the user providing feedback
            organization_id: Organization ID
            conversation_id: Optional conversation ID
            is_helpful: Whether response was helpful (true/false/null)
            star_rating: Star rating 1-5 (optional)
            feedback_text: Free text feedback (optional)
            feedback_category: Category: accuracy, relevance, clarity, safety, speed
            response_metadata: Additional response metadata
            user_metadata: Additional user metadata

        Returns:
            Feedback record with calculated trust_impact, or None on error
        """
        try:
            payload = {
                "response_id": response_id,
                "agent_id": agent_id,
                "user_id": user_id,
                "organization_id": organization_id,
            }

            # Add optional fields
            if conversation_id is not None:
                payload["conversation_id"] = conversation_id
            if is_helpful is not None:
                payload["is_helpful"] = is_helpful
            if star_rating is not None:
                payload["star_rating"] = star_rating
            if feedback_text:
                payload["feedback_text"] = feedback_text
            if feedback_category:
                payload["feedback_category"] = feedback_category
            if response_metadata:
                payload["response_metadata"] = response_metadata
            if user_metadata:
                payload["user_metadata"] = user_metadata

            session = await self._get_session()
            url = f"{self.api_base}/feedback/submit"

            logger.info(
                f"Submitting feedback to governance service: "
                f"agent={agent_id}, is_helpful={is_helpful}, rating={star_rating}"
            )

            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    feedback_data = data.get("feedback", {})
                    trust_impact = feedback_data.get("trust_impact_calculated")

                    logger.info(
                        f"✅ Feedback submitted successfully: "
                        f"trust_impact={trust_impact}%, "
                        f"feedback_id={feedback_data.get('id')}"
                    )

                    return feedback_data
                else:
                    error_text = await response.text()
                    logger.error(
                        f"❌ Governance service returned {response.status}: {error_text}"
                    )
                    return None

        except aiohttp.ClientConnectorError as e:
            logger.warning(
                f"⚠️ Cannot connect to governance service at {self.base_url}: {e}"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to submit feedback to governance service: {e}")
            return None

    async def get_trust_score(
        self,
        entity_id: str,
        entity_type: str = "agent"
    ) -> Optional[Dict[str, Any]]:
        """
        Get current trust score for an entity.

        Args:
            entity_id: Entity identifier
            entity_type: Entity type (user, agent, service)

        Returns:
            Trust score data or None on error
        """
        try:
            session = await self._get_session()
            url = f"{self.api_base}/trust/score/{entity_id}"
            params = {"entity_type": entity_type}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data")
                elif response.status == 404:
                    logger.info(f"No trust score found for {entity_type}:{entity_id}")
                    return None
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to get trust score: {response.status} - {error_text}"
                    )
                    return None

        except aiohttp.ClientConnectorError:
            logger.warning(f"Cannot connect to governance service at {self.base_url}")
            return None
        except Exception as e:
            logger.error(f"Error getting trust score: {e}")
            return None

    async def get_agent_feedback_stats(
        self,
        agent_id: str,
        days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Get aggregated feedback statistics for an agent.

        Args:
            agent_id: Agent identifier
            days: Number of days to look back

        Returns:
            Feedback statistics or None on error
        """
        try:
            session = await self._get_session()
            url = f"{self.api_base}/feedback/agent/{agent_id}/stats"
            params = {"days": days}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("stats")
                else:
                    logger.error(f"Failed to get feedback stats: {response.status}")
                    return None

        except aiohttp.ClientConnectorError:
            logger.warning(f"Cannot connect to governance service at {self.base_url}")
            return None
        except Exception as e:
            logger.error(f"Error getting feedback stats: {e}")
            return None


# Global governance client instance
_governance_client: Optional[GovernanceClient] = None


async def get_governance_client() -> GovernanceClient:
    """
    Get or create global governance client instance.

    Returns:
        GovernanceClient instance
    """
    global _governance_client

    if _governance_client is None:
        _governance_client = GovernanceClient()

    return _governance_client


async def close_governance_client():
    """Close global governance client."""
    global _governance_client

    if _governance_client:
        await _governance_client.close()
        _governance_client = None
