"""
Agent Service Layer for Agent-Chat
Provides abstraction between API and agent implementations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging
from pydantic import BaseModel, Field

from agents.registry import agent_registry
from core.config import settings

logger = logging.getLogger(__name__)


class AgentRequest(BaseModel):
    """Validated agent request model"""
    agent_id: str
    user_query: str
    file_ids: Optional[List[str]] = Field(default_factory=list)
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Standardized agent response model"""
    agent_id: str
    response: str
    confidence: float = Field(ge=0, le=1)
    execution_time: float
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    error: Optional[str] = None


class AgentService:
    """Service layer for agent operations"""
    
    def __init__(self):
        self.registry = agent_registry
        self.max_timeout = settings.agent_timeout_seconds
        self.max_retries = settings.agent_retry_attempts
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all available agents with their capabilities"""
        try:
            agents = []
            for agent_id, agent in self.registry._agents.items():
                agents.append({
                    "agent_id": agent_id,
                    "name": getattr(agent, "name", agent_id),
                    "description": getattr(agent, "description", ""),
                    "capabilities": getattr(agent, "capabilities", []),
                    "is_available": True,
                    "version": getattr(agent, "version", "1.0.0")
                })
            return agents
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            raise
    
    async def discover_agents(self, query: str) -> List[str]:
        """Discover suitable agents for a query"""
        try:
            suitable_agents = []
            
            # Simple keyword-based discovery
            query_lower = query.lower()
            
            for agent_id, agent in self.registry._agents.items():
                agent_desc = getattr(agent, "description", "").lower()
                agent_capabilities = getattr(agent, "capabilities", [])
                
                # Check if query matches description or capabilities
                if any(keyword in query_lower for keyword in agent_desc.split()):
                    suitable_agents.append(agent_id)
                elif any(cap.lower() in query_lower for cap in agent_capabilities):
                    suitable_agents.append(agent_id)
            
            # Default to orchestrator if no specific agent found
            if not suitable_agents and "orchestrator" in self.registry._agents:
                suitable_agents.append("orchestrator")
            
            return suitable_agents
        except Exception as e:
            logger.error(f"Error discovering agents: {e}")
            raise
    
    async def invoke_agent(self, request: AgentRequest) -> AgentResponse:
        """Invoke a specific agent with retry logic"""
        start_time = datetime.now()
        
        # Validate agent exists
        if request.agent_id not in self.registry._agents:
            return AgentResponse(
                agent_id=request.agent_id,
                response="",
                confidence=0,
                execution_time=0,
                error=f"Agent '{request.agent_id}' not found"
            )
        
        agent = self.registry._agents[request.agent_id]
        
        # Retry logic
        for attempt in range(self.max_retries):
            try:
                # Execute agent with timeout
                result = await asyncio.wait_for(
                    self._execute_agent(agent, request),
                    timeout=self.max_timeout
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return AgentResponse(
                    agent_id=request.agent_id,
                    response=result.get("response", ""),
                    confidence=result.get("confidence", 0.5),
                    execution_time=execution_time,
                    metadata=result.get("metadata", {})
                )
                
            except asyncio.TimeoutError:
                logger.warning(f"Agent {request.agent_id} timed out (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    return AgentResponse(
                        agent_id=request.agent_id,
                        response="",
                        confidence=0,
                        execution_time=self.max_timeout,
                        error="Agent execution timed out"
                    )
            except Exception as e:
                logger.error(f"Agent {request.agent_id} error (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    return AgentResponse(
                        agent_id=request.agent_id,
                        response="",
                        confidence=0,
                        execution_time=(datetime.now() - start_time).total_seconds(),
                        error=str(e)
                    )
            
            # Wait before retry
            await asyncio.sleep(2 ** attempt)
        
        return AgentResponse(
            agent_id=request.agent_id,
            response="",
            confidence=0,
            execution_time=(datetime.now() - start_time).total_seconds(),
            error="Max retries exceeded"
        )
    
    async def _execute_agent(self, agent, request: AgentRequest) -> Dict[str, Any]:
        """Execute agent with proper error handling"""
        try:
            # Build agent request
            agent_request = {
                "user_query": request.user_query,
                "file_ids": request.file_ids,
                "session_id": request.session_id,
                "metadata": request.metadata
            }
            
            # Call agent's process method
            if hasattr(agent, "process"):
                result = await agent.process(agent_request)
            elif hasattr(agent, "execute"):
                result = await agent.execute(agent_request)
            else:
                raise AttributeError(f"Agent {request.agent_id} has no process or execute method")
            
            # Ensure result is a dictionary
            if isinstance(result, str):
                result = {"response": result}
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing agent {request.agent_id}: {e}")
            raise
    
    async def orchestrate_agents(
        self,
        query: str,
        max_agents: int = 3,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Orchestrate multiple agents for complex queries"""
        try:
            # Discover suitable agents
            suitable_agents = await self.discover_agents(query)[:max_agents]
            
            if not suitable_agents:
                return {
                    "response": "No suitable agents found for your query",
                    "agents_used": [],
                    "confidence": 0
                }
            
            # Execute agents in parallel
            tasks = []
            for agent_id in suitable_agents:
                request = AgentRequest(
                    agent_id=agent_id,
                    user_query=query,
                    session_id=session_id
                )
                tasks.append(self.invoke_agent(request))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aggregate results
            valid_results = [
                r for r in results
                if isinstance(r, AgentResponse) and not r.error
            ]
            
            if not valid_results:
                return {
                    "response": "All agents failed to process the query",
                    "agents_used": suitable_agents,
                    "confidence": 0
                }
            
            # Select best response based on confidence
            best_result = max(valid_results, key=lambda r: r.confidence)
            
            return {
                "response": best_result.response,
                "agents_used": [r.agent_id for r in valid_results],
                "confidence": best_result.confidence,
                "execution_time": max(r.execution_time for r in valid_results),
                "metadata": {
                    "all_responses": [
                        {
                            "agent_id": r.agent_id,
                            "confidence": r.confidence,
                            "response": r.response[:200] + "..." if len(r.response) > 200 else r.response
                        }
                        for r in valid_results
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Error orchestrating agents: {e}")
            return {
                "response": f"Error orchestrating agents: {str(e)}",
                "agents_used": [],
                "confidence": 0
            }


# Singleton instance
agent_service = AgentService()
