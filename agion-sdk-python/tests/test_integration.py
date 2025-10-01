"""
Integration tests for Agion SDK with platform backend.

Tests SDK connectivity with:
- Gateway Service (agent registration, config fetching)
- Governance Service (policy sync)
- Redis Streams (event publishing)
"""

import asyncio
import pytest
import os
from datetime import datetime

from agion_sdk import AgionSDK, UserContext
from agion_sdk.types import EventType, EventSeverity, PolicyDecision
from agion_sdk.exceptions import (
    InitializationError,
    PolicyViolationError,
    ResourceNotFoundError,
)


# Test configuration from environment variables
GATEWAY_URL = os.getenv("AGION_GATEWAY_URL", "http://localhost:8080")
REDIS_URL = os.getenv("AGION_REDIS_URL", "redis://localhost:6379")
TEST_AGENT_ID = "langgraph-v2:test_agent"


@pytest.fixture
async def sdk():
    """Create and initialize SDK instance for testing."""
    sdk = AgionSDK(
        agent_id=TEST_AGENT_ID,
        agent_version="1.0.0",
        gateway_url=GATEWAY_URL,
        redis_url=REDIS_URL,
        policy_sync_enabled=True,
        policy_sync_interval=5,
    )

    await sdk.initialize()
    yield sdk
    await sdk.shutdown()


@pytest.fixture
def user_context():
    """Create test user context."""
    return UserContext(
        user_id="test-user-123",
        org_id="test-org-456",
        role="analyst",
        permissions=["read", "write", "execute_agents"],
        email="test@example.com",
    )


class TestSDKInitialization:
    """Test SDK initialization and connection."""

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful SDK initialization."""
        sdk = AgionSDK(
            agent_id=TEST_AGENT_ID,
            gateway_url=GATEWAY_URL,
            redis_url=REDIS_URL,
        )

        await sdk.initialize()
        assert sdk._initialized is True

        # Verify components are connected
        assert sdk.event_client._running is True
        assert sdk._http_session is not None
        if sdk.config.policy_sync_enabled:
            assert sdk._policy_sync is not None

        await sdk.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_invalid_gateway_url(self):
        """Test initialization with invalid gateway URL."""
        sdk = AgionSDK(
            agent_id=TEST_AGENT_ID,
            gateway_url="http://invalid-host-that-does-not-exist:9999",
            redis_url=REDIS_URL,
            policy_sync_enabled=False,  # Disable to avoid hanging
        )

        # Should still initialize (fails gracefully)
        await sdk.initialize()
        assert sdk._initialized is True

        await sdk.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_invalid_redis_url(self):
        """Test initialization with invalid Redis URL."""
        sdk = AgionSDK(
            agent_id=TEST_AGENT_ID,
            gateway_url=GATEWAY_URL,
            redis_url="redis://invalid-redis-host:6379",
        )

        with pytest.raises(InitializationError):
            await sdk.initialize()


class TestAgentRegistration:
    """Test agent registration with Gateway Service."""

    @pytest.mark.asyncio
    async def test_agent_registration(self, sdk):
        """Test agent registration endpoint."""
        # SDK should automatically register on initialization
        # Verify by checking if we can fetch agent info (requires backend API)

        # This is a smoke test - just verify SDK initialized successfully
        assert sdk._initialized is True
        assert sdk.config.agent_id == TEST_AGENT_ID


class TestPolicySync:
    """Test policy synchronization from Governance Service."""

    @pytest.mark.asyncio
    async def test_policy_sync_on_initialization(self, sdk):
        """Test that policies are synced on initialization."""
        # Wait for initial sync
        await asyncio.sleep(2)

        # Check if policy engine has policies loaded
        policies = sdk.policy_engine.get_policies()

        # May be empty if no policies configured in backend
        # Just verify the sync mechanism works
        assert isinstance(policies, list)

    @pytest.mark.asyncio
    async def test_policy_evaluation_local(self, sdk, user_context):
        """Test local policy evaluation."""
        # Test with default "allow all" policy
        result = await sdk.check_policy(
            action="test_action",
            user=user_context,
            resource="test_resource",
        )

        assert isinstance(result.decision, PolicyDecision)
        assert result.execution_time_ms < 5.0  # Should be < 1ms typically


class TestEventPublishing:
    """Test event publishing to Redis Streams."""

    @pytest.mark.asyncio
    async def test_publish_trust_event(self, sdk):
        """Test publishing trust event."""
        await sdk.event_client.publish_trust_event(
            agent_id=TEST_AGENT_ID,
            event_type=EventType.TASK_COMPLETED,
            severity=EventSeverity.POSITIVE,
            impact=0.05,
            confidence=0.95,
            context={"test": "data"},
        )

        # Wait for buffer flush
        await asyncio.sleep(6)

        # Verify event was published (check metrics)
        metrics = sdk.event_client.get_metrics()
        assert metrics["published"] >= 1

    @pytest.mark.asyncio
    async def test_publish_user_feedback(self, sdk):
        """Test publishing user feedback event."""
        await sdk.event_client.publish_user_feedback(
            execution_id="test-exec-123",
            user_id="test-user-123",
            feedback_type="thumbs_up",
            rating=5,
            comment="Great work!",
        )

        # Wait for buffer flush
        await asyncio.sleep(6)

        metrics = sdk.event_client.get_metrics()
        assert metrics["published"] >= 1

    @pytest.mark.asyncio
    async def test_publish_mission_event(self, sdk):
        """Test publishing mission event."""
        await sdk.event_client.publish_mission_event(
            mission_id="test-mission-123",
            event_type="joined",
            participant_id=TEST_AGENT_ID,
            data={"role": "worker"},
        )

        # Wait for buffer flush
        await asyncio.sleep(6)

        metrics = sdk.event_client.get_metrics()
        assert metrics["published"] >= 1


class TestDynamicConfiguration:
    """Test dynamic configuration fetching."""

    @pytest.mark.asyncio
    async def test_get_prompt_not_found(self, sdk):
        """Test fetching non-existent prompt."""
        with pytest.raises(ResourceNotFoundError):
            await sdk.get_prompt(location="non_existent_prompt")

    @pytest.mark.asyncio
    async def test_get_model_not_found(self, sdk):
        """Test fetching non-existent model."""
        with pytest.raises(ResourceNotFoundError):
            await sdk.get_model(purpose="non_existent_model")

    @pytest.mark.asyncio
    async def test_get_resource_not_found(self, sdk):
        """Test fetching non-existent resource."""
        with pytest.raises(ResourceNotFoundError):
            await sdk.get_resource(name="non_existent_resource")

    @pytest.mark.asyncio
    async def test_config_caching(self, sdk):
        """Test that configurations are cached."""
        # This test assumes no configs exist, so both calls should fail
        # but the second call should use cache (faster)

        try:
            await sdk.get_prompt(location="test_prompt", use_cache=False)
        except ResourceNotFoundError:
            pass

        # Check cache size
        initial_cache_size = len(sdk._prompt_cache)

        try:
            await sdk.get_prompt(location="test_prompt", use_cache=True)
        except ResourceNotFoundError:
            pass

        # Cache should not grow since resource doesn't exist
        assert len(sdk._prompt_cache) == initial_cache_size


class TestGovernanceDecorator:
    """Test governance decorator functionality."""

    @pytest.mark.asyncio
    async def test_governed_decorator_success(self, sdk, user_context):
        """Test successful execution with governance decorator."""

        @sdk.governed("test_agent", "test_action")
        async def test_function(data):
            return {"result": "success", "input": data}

        # Execute function with user context
        result = await test_function(
            {"test": "data"},
            _agion_user=user_context,
        )

        assert result["result"] == "success"
        assert result["input"]["test"] == "data"

    @pytest.mark.asyncio
    async def test_governed_decorator_with_policy_check(self, sdk, user_context):
        """Test decorator performs policy check."""

        call_count = 0

        @sdk.governed("test_agent", "sensitive_action")
        async def sensitive_function():
            nonlocal call_count
            call_count += 1
            return {"status": "executed"}

        # Should execute successfully (no blocking policies)
        result = await sensitive_function(_agion_user=user_context)

        assert call_count == 1
        assert result["status"] == "executed"


class TestMissionCoordination:
    """Test mission coordination functionality."""

    @pytest.mark.asyncio
    async def test_join_mission(self, sdk):
        """Test joining a mission."""
        mission_id = "test-mission-" + str(int(datetime.utcnow().timestamp()))

        await sdk.mission_client.join_mission(
            mission_id=mission_id,
            role="worker",
            initial_state={"status": "ready"},
        )

        assert mission_id in sdk.mission_client.get_active_missions()

    @pytest.mark.asyncio
    async def test_update_mission_state(self, sdk):
        """Test updating mission state."""
        mission_id = "test-mission-" + str(int(datetime.utcnow().timestamp()))

        await sdk.mission_client.join_mission(
            mission_id=mission_id,
            role="worker",
        )

        await sdk.mission_client.update_state(
            mission_id=mission_id,
            state={"status": "working", "progress": 50},
        )

        # Verify state updated
        assert mission_id in sdk.mission_client._active_missions
        participant = sdk.mission_client._active_missions[mission_id]
        assert participant.state["progress"] == 50

    @pytest.mark.asyncio
    async def test_send_mission_message(self, sdk):
        """Test sending mission message."""
        mission_id = "test-mission-" + str(int(datetime.utcnow().timestamp()))

        await sdk.mission_client.join_mission(
            mission_id=mission_id,
            role="coordinator",
        )

        await sdk.mission_client.send_message(
            mission_id=mission_id,
            message_type="task_assignment",
            content={"task": "analyze_data", "priority": "high"},
        )

        # Wait for message to be published
        await asyncio.sleep(6)

        metrics = sdk.event_client.get_metrics()
        assert metrics["published"] >= 1

    @pytest.mark.asyncio
    async def test_leave_mission(self, sdk):
        """Test leaving a mission."""
        mission_id = "test-mission-" + str(int(datetime.utcnow().timestamp()))

        await sdk.mission_client.join_mission(
            mission_id=mission_id,
            role="worker",
        )

        assert mission_id in sdk.mission_client.get_active_missions()

        await sdk.mission_client.leave_mission(mission_id)

        assert mission_id not in sdk.mission_client.get_active_missions()


class TestSDKMetrics:
    """Test SDK metrics collection."""

    @pytest.mark.asyncio
    async def test_get_metrics(self, sdk):
        """Test retrieving SDK metrics."""
        metrics = sdk.get_metrics()

        assert "policy_engine" in metrics
        assert "event_client" in metrics
        assert "cache_sizes" in metrics

        # Verify structure
        assert "total_evaluations" in metrics["policy_engine"]
        assert "published" in metrics["event_client"]
        assert "prompts" in metrics["cache_sizes"]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
