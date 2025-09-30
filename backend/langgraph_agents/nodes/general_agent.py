"""
General Agent Node - Conversational AI assistant

Handles general questions, conversations, and assistance using Claude Sonnet 4.5.
Provides helpful, accurate responses without follow-up questions.
"""

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from langgraph_agents.state import AgentState
from langgraph_agents.tools.database_tools import load_session_messages, get_database_session
from core.config import settings


async def general_agent_node(state: AgentState) -> AgentState:
    """
    General agent for conversation and Q&A.

    Args:
        state: Current agent state with query and conversation history

    Returns:
        AgentState: Updated state with response
    """
    query = state["query"]
    session_id = state["session_id"]

    try:
        # Load conversation history
        async for db in get_database_session():
            history = await load_session_messages(db, session_id, limit=20)
            break

        # Initialize GPT-5 via Requesty AI
        llm = ChatOpenAI(
            model="openai/gpt-5-chat-latest",
            api_key=settings.REQUESTY_AI_API_KEY,
            base_url=settings.REQUESTY_AI_API_BASE,
            temperature=0.7,
        )

        # Build messages for Claude
        system_prompt = """You are a helpful AI assistant in the Agent-Chat system.

Guidelines:
- Provide clear, accurate, and helpful responses
- Be concise but complete
- Do NOT ask follow-up questions (user requirement)
- If you need more information, make reasonable assumptions or explain what's missing
- Use a friendly, professional tone
- Format responses with markdown when appropriate
- If discussing data analysis, explain clearly but don't create charts (that's for the Chart Agent)

Remember: The user has explicitly requested NO follow-up questions in responses."""

        messages = [SystemMessage(content=system_prompt)]

        # Add conversation history
        for msg in history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))

        # Add current query
        messages.append(HumanMessage(content=query))

        # Get response from Claude
        response = await llm.ainvoke(messages)
        response_text = response.content

        # Ensure no follow-up questions
        # (Claude should already follow system prompt, but this is a safety check)
        response_text = remove_followup_questions(response_text)

        return {
            **state,
            "agent_response": response_text,
            "confidence": 1.0,
            "execution_path": state.get("execution_path", []) + ["general_agent"],
            "metadata": {
                **state.get("metadata", {}),
                "history_length": len(history),
            },
        }

    except Exception as e:
        # Error handling
        return {
            **state,
            "agent_response": "I apologize, but I encountered an error processing your request. Please try again.",
            "confidence": 0.0,
            "execution_path": state.get("execution_path", []) + ["general_agent"],
            "error": str(e),
        }


def remove_followup_questions(text: str) -> str:
    """
    Remove common follow-up question patterns from response.

    Args:
        text: Response text

    Returns:
        str: Text without follow-up questions
    """
    # Common follow-up patterns to remove
    followup_patterns = [
        "Would you like",
        "Do you want",
        "Should I",
        "Can I help you with",
        "Is there anything else",
        "What would you like",
        "How can I assist",
    ]

    lines = text.split("\n")
    filtered_lines = []

    for line in lines:
        # Check if line starts with a follow-up pattern
        is_followup = any(line.strip().startswith(pattern) for pattern in followup_patterns)

        # Also check for question marks at end of sentences
        if is_followup or (line.strip().endswith("?") and any(pattern.lower() in line.lower() for pattern in followup_patterns)):
            continue

        filtered_lines.append(line)

    return "\n".join(filtered_lines).strip()