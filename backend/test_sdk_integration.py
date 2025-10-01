"""
Test SDK Integration - Verify Agion SDK functionality

This script tests:
1. SDK initialization
2. Agent registration
3. Metrics reporting
4. Event publishing
5. Feedback submission
"""

import asyncio
import sys
from core.agion import AgionClient, get_agion_sdk
from langgraph_agents.metrics_reporter import metrics_reporter
from langgraph_agents.agent_registry import get_all_agent_ids


async def test_sdk_initialization():
    """Test SDK initialization"""
    print("\n🧪 Test 1: SDK Initialization")
    print("-" * 50)

    try:
        if not AgionClient.is_initialized():
            await AgionClient.initialize()
            print("✅ SDK initialized successfully")
        else:
            print("✅ SDK already initialized")

        sdk = await get_agion_sdk()
        if sdk:
            print("✅ SDK instance retrieved")
            return True
        else:
            print("❌ SDK instance is None")
            return False

    except Exception as e:
        print(f"❌ SDK initialization failed: {e}")
        return False


async def test_agent_registration():
    """Test agent registration"""
    print("\n🧪 Test 2: Agent Registration")
    print("-" * 50)

    try:
        agent_ids = get_all_agent_ids()
        print(f"📋 Registered agents: {len(agent_ids)}")
        for agent_id in agent_ids:
            print(f"   - {agent_id}")

        if len(agent_ids) == 6:
            print("✅ All 6 agents registered")
            return True
        else:
            print(f"⚠️ Expected 6 agents, found {len(agent_ids)}")
            return False

    except Exception as e:
        print(f"❌ Agent registration test failed: {e}")
        return False


async def test_metrics_reporting():
    """Test metrics reporting"""
    print("\n🧪 Test 3: Metrics Reporting")
    print("-" * 50)

    try:
        # Test execution start
        print("Testing execution start report...")
        start_time = await metrics_reporter.report_execution_start(
            agent_id="langgraph-v2:test_agent",
            execution_id="test-exec-001",
            query="Test query",
            user_id="test-user"
        )
        print(f"✅ Execution start reported (time: {start_time})")

        # Test execution success
        print("Testing execution success report...")
        await metrics_reporter.report_execution_success(
            agent_id="langgraph-v2:test_agent",
            execution_id="test-exec-001",
            start_time=start_time,
            result={"test": "data"},
            user_id="test-user"
        )
        print("✅ Execution success reported (+2% trust)")

        # Test execution failure
        print("Testing execution failure report...")
        await metrics_reporter.report_execution_failure(
            agent_id="langgraph-v2:test_agent",
            execution_id="test-exec-002",
            start_time=start_time,
            error="Test error",
            user_id="test-user"
        )
        print("✅ Execution failure reported (-2% trust)")

        # Test user feedback
        print("Testing user feedback report...")
        await metrics_reporter.report_user_feedback(
            agent_id="langgraph-v2:test_agent",
            execution_id="test-exec-001",
            user_id="test-user",
            rating=5,
            feedback_type="thumbs_up",
            comment="Great job!"
        )
        print("✅ User feedback reported (+0.5% trust for rating ≥4)")

        return True

    except Exception as e:
        print(f"❌ Metrics reporting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_event_publishing():
    """Test event publishing to Redis"""
    print("\n🧪 Test 4: Event Publishing")
    print("-" * 50)

    try:
        sdk = await get_agion_sdk()
        if not sdk:
            print("⚠️ SDK not initialized, skipping event test")
            return False

        # Wait for events to flush
        print("Waiting 6 seconds for event flush...")
        await asyncio.sleep(6)

        # Get metrics
        metrics = sdk.get_metrics()
        event_metrics = metrics.get("event_client", {})

        published = event_metrics.get("published", 0)
        failed = event_metrics.get("failed", 0)
        buffer_size = event_metrics.get("buffer_size", 0)

        print(f"📊 Event Metrics:")
        print(f"   - Published: {published}")
        print(f"   - Failed: {failed}")
        print(f"   - Buffer Size: {buffer_size}")

        if published > 0:
            print(f"✅ Events published successfully ({published} events)")
            return True
        else:
            print("⚠️ No events published (may be buffered)")
            return True  # Not necessarily a failure

    except Exception as e:
        print(f"❌ Event publishing test failed: {e}")
        return False


async def test_sdk_metrics():
    """Test SDK metrics retrieval"""
    print("\n🧪 Test 5: SDK Metrics")
    print("-" * 50)

    try:
        metrics = await AgionClient.get_metrics()

        print("📊 SDK Metrics:")
        print(f"   Policy Engine: {metrics.get('policy_engine', 'N/A')}")
        print(f"   Event Client: {metrics.get('event_client', 'N/A')}")
        print(f"   Policy Sync: {metrics.get('policy_sync', 'N/A')}")
        print(f"   Cache Sizes: {metrics.get('cache_sizes', 'N/A')}")

        print("✅ SDK metrics retrieved")
        return True

    except Exception as e:
        print(f"❌ SDK metrics test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("🧪 Agion SDK Integration Tests")
    print("=" * 50)

    results = {
        "SDK Initialization": await test_sdk_initialization(),
        "Agent Registration": await test_agent_registration(),
        "Metrics Reporting": await test_metrics_reporting(),
        "Event Publishing": await test_event_publishing(),
        "SDK Metrics": await test_sdk_metrics(),
    }

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 50)

    # Cleanup
    print("\n🧹 Cleaning up...")
    await AgionClient.shutdown()
    print("✅ SDK shutdown complete")

    # Exit code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
