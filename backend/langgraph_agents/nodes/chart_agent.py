"""
Chart Agent Node - Data visualization specialist

Creates beautiful, interactive charts from uploaded data using:
- GPT-5 for code generation
- Plotly for chart rendering
- Azure Blob Storage for file access
"""

from typing import Dict, Any
import traceback

from langgraph_agents.state import AgentState
from langgraph_agents.tools.database_tools import load_file_metadata, get_database_session
from langgraph_agents.tools.storage_tools import load_file_from_storage
from langgraph_agents.tools.chart_tools import create_chart, validate_dataframe_for_chart
from langgraph_agents.governance_wrapper import governed_node

# Get session_id at module level for chart storage
def get_session_id_from_state(state):
    return state.get("session_id", "default")


@governed_node("chart_agent", "generate_chart")
async def chart_agent_node(state: AgentState) -> AgentState:
    """
    Chart agent that generates visualizations from data.

    Args:
        state: Current agent state with query and file references

    Returns:
        AgentState: Updated state with chart or error
    """
    query = state["query"]
    file_ids = state.get("uploaded_files", [])

    # Validate file availability
    if not file_ids:
        return {
            **state,
            "agent_response": "I need at least one data file to create a chart. Please upload a CSV or Excel file.",
            "confidence": 1.0,
            "execution_path": state.get("execution_path", []) + ["chart_agent"],
            "error": "No files uploaded",
        }

    try:
        # Load file metadata from database
        async for db in get_database_session():
            file_metadata = await load_file_metadata(db, file_ids)
            break

        if not file_metadata:
            return {
                **state,
                "agent_response": "I couldn't find the uploaded files. Please try uploading again.",
                "confidence": 1.0,
                "execution_path": state.get("execution_path", []) + ["chart_agent"],
                "error": "File metadata not found",
            }

        # Load first file (for now, we'll handle multi-file later)
        file = file_metadata[0]
        df = await load_file_from_storage(file.file_path)

        if df is None:
            return {
                **state,
                "agent_response": f"I couldn't load the file '{file.original_filename}'. Please check the file format (CSV or Excel).",
                "confidence": 1.0,
                "execution_path": state.get("execution_path", []) + ["chart_agent"],
                "error": "Failed to load file from storage",
            }

        # Validate dataframe
        is_valid, validation_error = validate_dataframe_for_chart(df)
        if not is_valid:
            return {
                **state,
                "agent_response": f"I cannot create a chart: {validation_error}",
                "confidence": 1.0,
                "execution_path": state.get("execution_path", []) + ["chart_agent"],
                "error": validation_error,
            }

        # Create chart using GPT-5 via Requesty
        chart_result = await create_chart(
            user_query=query,
            df=df,
            model="openai/gpt-5-chat-latest",
        )

        if not chart_result["success"]:
            return {
                **state,
                "agent_response": f"❌ Chart generation failed: {chart_result['error']}",
                "confidence": 0.5,
                "execution_path": state.get("execution_path", []) + ["chart_agent"],
                "error": chart_result["error"],
            }

        # Store chart in blob storage for persistence and easy downloading
        from langgraph_agents.tools.storage_tools import save_chart_to_storage
        from datetime import datetime
        import uuid

        session_id = state.get("session_id", "default")
        chart_id = str(uuid.uuid4())
        chart_filename = f"charts/{session_id}/{datetime.utcnow().strftime('%Y/%m/%d')}/{chart_id}.html"

        # Save HTML chart to storage
        chart_url = None
        if chart_result["chart_html"]:
            try:
                chart_url = await save_chart_to_storage(
                    chart_data=chart_result["chart_html"].encode('utf-8'),
                    filename=chart_filename,
                )
            except Exception as e:
                print(f"Warning: Could not save chart to storage: {e}")

        # Success - return chart
        response_text = f"✅ Here's your chart based on '{file.original_filename}':"

        return {
            **state,
            "agent_response": response_text,
            "agent_data": {
                "chart_html": chart_result["chart_html"],
                "chart_png": chart_result["chart_png"],
                "chart_url": chart_url,  # Permanent storage URL
                "chart_id": chart_id,
                "generated_code": chart_result.get("code"),
                "file_name": file.original_filename,
                "data_rows": len(df),
                "data_columns": len(df.columns),
            },
            "confidence": 1.0,
            "execution_path": state.get("execution_path", []) + ["chart_agent"],
        }

    except Exception as e:
        # Unexpected error
        error_trace = traceback.format_exc()
        return {
            **state,
            "agent_response": f"❌ An unexpected error occurred while creating the chart: {str(e)}",
            "confidence": 0.0,
            "execution_path": state.get("execution_path", []) + ["chart_agent"],
            "error": str(e),
            "error_details": {"traceback": error_trace},
        }