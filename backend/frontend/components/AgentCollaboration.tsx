"""
React Component for Visualizing Agent Collaboration
Shows multiple agents working together with real-time status updates
"""

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface Agent {
  agent_id: string;
  agent_name: string;
  agent_role: string;
  status: 'waiting' | 'thinking' | 'typing' | 'completed';
  current_task: string;
  progress: number;
  message?: string;
  emoji?: string;
}

interface AgentCardProps {
  agent: Agent;
  typingPreview?: string;
}

const AgentCard: React.FC<AgentCardProps> = ({ agent, typingPreview }) => {
  const getStatusColor = () => {
    switch (agent.status) {
      case 'waiting': return 'bg-gray-100';
      case 'thinking': return 'bg-yellow-50';
      case 'typing': return 'bg-blue-50';
      case 'completed': return 'bg-green-50';
      default: return 'bg-white';
    }
  };

  const getStatusIcon = () => {
    switch (agent.status) {
      case 'waiting': return '⏳';
      case 'thinking': return '🤔';
      case 'typing': return '✍️';
      case 'completed': return '✅';
      default: return '🤖';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className={`p-4 rounded-lg shadow-md ${getStatusColor()} transition-all duration-300`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center">
          <span className="text-2xl mr-2">{agent.emoji || '🤖'}</span>
          <div>
            <h3 className="font-semibold text-gray-800">{agent.agent_name}</h3>
            <p className="text-sm text-gray-600">{agent.agent_role}</p>
          </div>
        </div>
        <span className="text-xl">{getStatusIcon()}</span>
      </div>

      <div className="mt-3">
        <p className="text-sm text-gray-700">{agent.current_task}</p>

        {/* Progress bar */}
        <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
          <motion.div
            className="bg-blue-600 h-2 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${agent.progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>

        {/* Typing animation */}
        {agent.status === 'typing' && typingPreview && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-2 p-2 bg-white rounded text-sm text-gray-600 font-mono"
          >
            {typingPreview}
            <motion.span
              animate={{ opacity: [1, 0] }}
              transition={{ repeat: Infinity, duration: 0.8 }}
            >
              |
            </motion.span>
          </motion.div>
        )}

        {/* Completion message */}
        {agent.status === 'completed' && agent.message && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mt-2 p-2 bg-white rounded text-sm text-gray-700"
          >
            {agent.message}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

interface AgentCollaborationProps {
  query: string;
  onComplete?: (result: any) => void;
}

export const AgentCollaboration: React.FC<AgentCollaborationProps> = ({
  query,
  onComplete
}) => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [queryType, setQueryType] = useState<string>('');
  const [orchestratorMessage, setOrchestratorMessage] = useState<string>('');
  const [isComplete, setIsComplete] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws/agents/collaborate');
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      // Send query
      ws.send(JSON.stringify({
        type: 'query',
        query: query,
        data: {}
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [query]);

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'orchestrator_update':
        setOrchestratorMessage(data.message);
        break;

      case 'team_composition':
        setQueryType(data.query_type);
        // Initialize agents from team composition
        const initialAgents = data.agents.map((a: any) => ({
          agent_id: a.agent_id || Math.random().toString(),
          agent_name: a.name,
          agent_role: a.role,
          status: 'waiting',
          current_task: 'Preparing...',
          progress: 0,
          emoji: a.emoji
        }));
        setAgents(initialAgents);
        break;

      case 'agents_status':
        setAgents(data.agents);
        break;

      case 'agent_update':
        setAgents(prev => prev.map(a =>
          a.agent_id === data.agent.agent_id ? data.agent : a
        ));
        break;

      case 'agent_complete':
        setAgents(prev => prev.map(a =>
          a.agent_id === data.agent.agent_id
            ? { ...data.agent, status: 'completed' }
            : a
        ));
        break;

      case 'synthesis':
        setOrchestratorMessage(data.message);
        break;

      case 'final_response':
        setIsComplete(true);
        if (onComplete) {
          onComplete(data.response);
        }
        break;
    }
  };

  return (
    <div className="p-6 bg-gray-50 rounded-lg">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          🤖 Agent Collaboration
        </h2>
        {queryType && (
          <p className="text-sm text-gray-600">
            Query Type: <span className="font-semibold">{queryType}</span>
          </p>
        )}
        {orchestratorMessage && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-sm text-blue-600 mt-2"
          >
            {orchestratorMessage}
          </motion.p>
        )}
      </div>

      {/* Agent Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <AnimatePresence>
          {agents.map((agent) => (
            <AgentCard
              key={agent.agent_id}
              agent={agent}
              typingPreview={
                agent.status === 'typing'
                  ? `Processing ${agent.current_task}...`
                  : undefined
              }
            />
          ))}
        </AnimatePresence>
      </div>

      {/* Completion Status */}
      {isComplete && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 p-4 bg-green-100 rounded-lg"
        >
          <div className="flex items-center">
            <span className="text-2xl mr-2">🎉</span>
            <p className="text-green-800 font-semibold">
              Analysis complete! All agents have finished their tasks.
            </p>
          </div>
        </motion.div>
      )}

      {/* Connection Status */}
      <div className="mt-4 text-xs text-gray-500 text-right">
        {wsRef.current?.readyState === WebSocket.OPEN ? (
          <span className="text-green-600">● Connected</span>
        ) : (
          <span className="text-red-600">● Disconnected</span>
        )}
      </div>
    </div>
  );
};

// CSS for typing animation
const typingAnimationCSS = `
  @keyframes typing {
    from { width: 0 }
    to { width: 100% }
  }

  @keyframes blink-caret {
    from, to { border-color: transparent }
    50% { border-color: currentColor }
  }

  .typing-effect {
    overflow: hidden;
    border-right: .15em solid currentColor;
    white-space: nowrap;
    animation:
      typing 3.5s steps(40, end),
      blink-caret .75s step-end infinite;
  }
`;

export default AgentCollaboration;