"""
Quick connectivity test for backend services.

Run this to verify SDK can connect to platform backend:
    python -m tests.test_backend_connectivity
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agion_sdk import AgionSDK
from agion_sdk.types import EventType, EventSeverity


async def test_connectivity():
    """Test connectivity to all backend services."""

    # Configuration
    gateway_url = os.getenv("AGION_GATEWAY_URL", "http://localhost:8080")
    redis_url = os.getenv("AGION_REDIS_URL", "redis://localhost:6379")
    agent_id = "test:connectivity_check"

    print("=" * 60)
    print("Agion SDK Backend Connectivity Test")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Gateway URL: {gateway_url}")
    print(f"  Redis URL:   {redis_url}")
    print(f"  Agent ID:    {agent_id}")
    print()

    sdk = AgionSDK(
        agent_id=agent_id,
        agent_version="1.0.0",
        gateway_url=gateway_url,
        redis_url=redis_url,
        policy_sync_enabled=True,
        policy_sync_interval=10,
        event_flush_interval=2,
    )

    tests_passed = 0
    tests_failed = 0

    try:
        # Test 1: SDK Initialization
        print("[1/7] Testing SDK initialization...")
        try:
            await sdk.initialize()
            print("      ✓ SDK initialized successfully")
            tests_passed += 1
        except Exception as e:
            print(f"      ✗ FAILED: {str(e)}")
            tests_failed += 1
            return

        # Test 2: HTTP Session
        print("[2/7] Testing HTTP session to Gateway...")
        try:
            assert sdk._http_session is not None
            print("      ✓ HTTP session created")
            tests_passed += 1
        except Exception as e:
            print(f"      ✗ FAILED: {str(e)}")
            tests_failed += 1

        # Test 3: Redis Connection
        print("[3/7] Testing Redis connection...")
        try:
            assert sdk.event_client._redis is not None
            # Try to ping Redis
            await sdk.event_client._redis.ping()
            print("      ✓ Redis connected and responding")
            tests_passed += 1
        except Exception as e:
            print(f"      ✗ FAILED: {str(e)}")
            tests_failed += 1

        # Test 4: Policy Sync
        print("[4/7] Testing policy sync from Governance Service...")
        try:
            # Wait for initial sync
            await asyncio.sleep(3)

            policies = sdk.policy_engine.get_policies()
            sync_metrics = sdk._policy_sync.get_metrics() if sdk._policy_sync else {}

            print(f"      ✓ Policy sync working")
            print(f"        - Loaded: {len(policies)} policies")
            print(f"        - Sync count: {sync_metrics.get('sync_count', 0)}")
            print(f"        - Errors: {sync_metrics.get('sync_errors', 0)}")
            tests_passed += 1
        except Exception as e:
            print(f"      ✗ FAILED: {str(e)}")
            tests_failed += 1

        # Test 5: Event Publishing
        print("[5/7] Testing event publishing to Redis Streams...")
        try:
            # Publish test event
            await sdk.event_client.publish_trust_event(
                agent_id=agent_id,
                event_type=EventType.TASK_COMPLETED,
                severity=EventSeverity.POSITIVE,
                impact=0.01,
                confidence=1.0,
                context={"test": "connectivity_check"},
            )

            # Wait for flush
            await asyncio.sleep(3)

            event_metrics = sdk.event_client.get_metrics()
            print(f"      ✓ Event publishing working")
            print(f"        - Published: {event_metrics.get('published', 0)}")
            print(f"        - Failed: {event_metrics.get('failed', 0)}")
            print(f"        - Buffer: {event_metrics.get('buffer_size', 0)}")
            tests_passed += 1
        except Exception as e:
            print(f"      ✗ FAILED: {str(e)}")
            tests_failed += 1

        # Test 6: Configuration Fetching
        print("[6/7] Testing configuration endpoints...")
        try:
            # Try to fetch a prompt (will fail if doesn't exist, which is OK)
            try:
                await sdk.get_prompt(location="test_prompt_nonexistent")
                print("      ✓ Prompt endpoint accessible (prompt found)")
            except Exception as e:
                if "not found" in str(e).lower():
                    print("      ✓ Prompt endpoint accessible (404 as expected)")
                else:
                    raise
            tests_passed += 1
        except Exception as e:
            print(f"      ✗ FAILED: {str(e)}")
            tests_failed += 1

        # Test 7: Policy Evaluation
        print("[7/7] Testing local policy evaluation...")
        try:
            result = await sdk.check_policy(
                action="test_action",
                resource="test_resource",
            )

            print(f"      ✓ Policy evaluation working")
            print(f"        - Decision: {result.decision}")
            print(f"        - Latency: {result.execution_time_ms:.3f}ms")
            print(f"        - Policies checked: {len(result.matched_policies)}")
            tests_passed += 1
        except Exception as e:
            print(f"      ✗ FAILED: {str(e)}")
            tests_failed += 1

        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"Tests passed: {tests_passed}/7")
        print(f"Tests failed: {tests_failed}/7")

        if tests_failed == 0:
            print("\n✅ All connectivity tests PASSED!")
            print("\nYour SDK is properly connected to the backend services.")
            print("You can now use the SDK in your agents.")
        else:
            print(f"\n⚠️  {tests_failed} test(s) FAILED")
            print("\nPlease check the errors above and verify:")
            print("  1. Gateway Service is running at", gateway_url)
            print("  2. Redis is running at", redis_url)
            print("  3. Network connectivity between agent and services")
            print("  4. Firewall rules allow communication")

        # Display metrics
        print("\n" + "=" * 60)
        print("SDK Metrics")
        print("=" * 60)
        metrics = sdk.get_metrics()

        print("\nPolicy Engine:")
        for key, value in metrics.get("policy_engine", {}).items():
            print(f"  {key}: {value}")

        print("\nEvent Client:")
        for key, value in metrics.get("event_client", {}).items():
            print(f"  {key}: {value}")

        print("\nCache Sizes:")
        for key, value in metrics.get("cache_sizes", {}).items():
            print(f"  {key}: {value}")

        print()

    finally:
        print("Shutting down SDK...")
        await sdk.shutdown()
        print("Done.\n")


if __name__ == "__main__":
    try:
        asyncio.run(test_connectivity())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
