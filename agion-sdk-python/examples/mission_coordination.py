"""
Example: Multi-agent mission coordination with Agion SDK

This example shows how multiple agents coordinate on a shared mission.
"""

import asyncio
from agion_sdk import AgionSDK


async def data_collector_agent():
    """Agent that collects data for the mission."""
    sdk = AgionSDK(
        agent_id="langgraph-v2:data_collector",
        gateway_url="http://localhost:8080",
        redis_url="redis://localhost:6379",
    )

    await sdk.initialize()

    try:
        mission_id = "mission-dashboard-123"

        # Join mission
        await sdk.mission_client.join_mission(
            mission_id=mission_id,
            role="data_collector",
            initial_state={"status": "collecting", "progress": 0},
        )

        print("Data Collector: Joined mission")

        # Simulate data collection
        for i in range(1, 6):
            await asyncio.sleep(1)

            # Update state
            await sdk.mission_client.update_state(
                mission_id=mission_id,
                state={"progress": i * 20, "records_collected": i * 100},
            )

            print(f"Data Collector: Collected {i * 100} records")

        # Send completion message
        await sdk.mission_client.send_message(
            mission_id=mission_id,
            message_type="data_ready",
            content={
                "total_records": 500,
                "data_url": "s3://bucket/data.csv",
            },
        )

        print("Data Collector: Data collection complete")

        # Leave mission
        await sdk.mission_client.leave_mission(mission_id)

    finally:
        await sdk.shutdown()


async def chart_generator_agent():
    """Agent that generates charts from collected data."""
    sdk = AgionSDK(
        agent_id="langgraph-v2:chart_generator",
        gateway_url="http://localhost:8080",
        redis_url="redis://localhost:6379",
    )

    await sdk.initialize()

    try:
        mission_id = "mission-dashboard-123"

        # Join mission
        await sdk.mission_client.join_mission(
            mission_id=mission_id,
            role="chart_generator",
            initial_state={"status": "waiting", "charts_generated": 0},
        )

        print("Chart Generator: Joined mission")

        # Wait for data (in real app, would listen to Redis Streams)
        await asyncio.sleep(6)

        # Simulate chart generation
        for i in range(1, 4):
            await asyncio.sleep(1)

            await sdk.mission_client.update_state(
                mission_id=mission_id,
                state={"status": "generating", "charts_generated": i},
            )

            print(f"Chart Generator: Generated chart {i}")

        # Send completion message
        await sdk.mission_client.send_message(
            mission_id=mission_id,
            message_type="charts_ready",
            content={
                "total_charts": 3,
                "chart_urls": [
                    "s3://bucket/chart1.png",
                    "s3://bucket/chart2.png",
                    "s3://bucket/chart3.png",
                ],
            },
        )

        print("Chart Generator: Charts complete")

        # Leave mission
        await sdk.mission_client.leave_mission(mission_id)

    finally:
        await sdk.shutdown()


async def dashboard_assembler_agent():
    """Agent that assembles the final dashboard."""
    sdk = AgionSDK(
        agent_id="langgraph-v2:dashboard_assembler",
        gateway_url="http://localhost:8080",
        redis_url="redis://localhost:6379",
    )

    await sdk.initialize()

    try:
        mission_id = "mission-dashboard-123"

        # Join mission
        await sdk.mission_client.join_mission(
            mission_id=mission_id,
            role="dashboard_assembler",
            initial_state={"status": "waiting"},
        )

        print("Dashboard Assembler: Joined mission")

        # Wait for all components (in real app, would listen to Redis Streams)
        await asyncio.sleep(10)

        # Assemble dashboard
        await sdk.mission_client.update_state(
            mission_id=mission_id,
            state={"status": "assembling"},
        )

        print("Dashboard Assembler: Assembling dashboard")
        await asyncio.sleep(2)

        # Send completion message
        await sdk.mission_client.send_message(
            mission_id=mission_id,
            message_type="dashboard_ready",
            content={
                "dashboard_url": "https://app.example.com/dashboards/123",
            },
        )

        print("Dashboard Assembler: Dashboard complete!")

        # Leave mission
        await sdk.mission_client.leave_mission(mission_id)

    finally:
        await sdk.shutdown()


async def main():
    """Run all agents in parallel for mission coordination."""
    print("Starting multi-agent mission: Dashboard Generation\n")

    # Run all agents concurrently
    await asyncio.gather(
        data_collector_agent(),
        chart_generator_agent(),
        dashboard_assembler_agent(),
    )

    print("\nMission complete!")


if __name__ == "__main__":
    asyncio.run(main())
