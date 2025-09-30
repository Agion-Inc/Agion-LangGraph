/**
 * Agent-Chat Agents Page
 * Browse and interact with available AI agents
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  CpuChipIcon,
  MagnifyingGlassIcon,
  ChatBubbleLeftRightIcon,
  InformationCircleIcon,
  SparklesIcon
} from '@heroicons/react/24/outline'
import { useAgentStore } from '../hooks/useAgents'
import { useChatInputState } from '../hooks/useChatInputState'
import { FilesChatInput } from '../components/chat/FilesChatInput'

export const AgentsPage: React.FC = () => {
  const navigate = useNavigate()
  const { agents, loadAgents, isLoading, error } = useAgentStore()
  const { setMessage } = useChatInputState()
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadAgents().catch((err) => {
      console.error('Failed to load agents:', err)
      // Error is handled by the store, just log it
    })
  }, [loadAgents])

  // Filter agents based on search
  const filteredAgents = agents.filter(agent =>
    agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (agent.description && agent.description.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (agent.capabilities && agent.capabilities.some(cap => cap.toLowerCase().includes(searchTerm.toLowerCase())))
  )

  const getAgentIcon = (agentType: string) => {
    switch (agentType.toLowerCase()) {
      case 'data_analyst':
        return '📊'
      case 'financial_analyst':
        return '💰'
      case 'research_assistant':
        return '🔍'
      case 'code_assistant':
        return '💻'
      case 'content_writer':
        return '✍️'
      case 'project_manager':
        return '📋'
      default:
        return '🤖'
    }
  }

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      active: { color: 'green', icon: '✓', label: 'Active' },
      busy: { color: 'yellow', icon: '⏳', label: 'Busy' },
      offline: { color: 'gray', icon: '○', label: 'Offline' },
    }

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.offline

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-${config.color}-100 text-${config.color}-800`}>
        {config.icon} {config.label}
      </span>
    )
  }

  const handleChatWithAgent = (agentId: string) => {
    // Find the agent to get its name
    const agent = agents.find(a => a.agent_id === agentId)
    if (agent) {
      // Set up the input text with the agent tag
      setMessage(`@agent:${agent.name} `)
    }
    // Navigate to the chat view
    navigate('/chat')
  }

  return (
    <div className="flex flex-col h-full">
      {/* Agents Content Area */}
      <div className="flex-1 overflow-y-auto bg-gray-50">
        {/* Search Header */}
        <div className="bg-white shadow-sm border-b sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center space-x-4 flex-1">
                <MagnifyingGlassIcon className="w-5 h-5 text-gray-400 flex-shrink-0" />
                <input
                  type="text"
                  placeholder="Search agents..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 max-w-2xl border-none focus:outline-none focus:ring-0 text-gray-900 placeholder-gray-500 text-base"
                />
                <span className="text-sm text-gray-500 whitespace-nowrap">
                  {filteredAgents.length} agent{filteredAgents.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

          {/* Agents Grid */}
          <div className="bg-white rounded-lg shadow">
            {isLoading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-gray-600">Loading agents...</p>
              </div>
            ) : error ? (
              <div className="p-8 text-center">
                <div className="text-red-500 mb-4">
                  <InformationCircleIcon className="w-8 h-8 mx-auto" />
                </div>
                <p className="text-gray-600">{error}</p>
              </div>
            ) : filteredAgents.length === 0 ? (
              <div className="p-8 text-center">
                <CpuChipIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {searchTerm ? 'No agents found' : 'No agents available'}
                </h3>
                <p className="text-gray-600">
                  {searchTerm 
                    ? 'Try adjusting your search term'
                    : 'No AI agents are currently configured'
                  }
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
                {filteredAgents.map((agent, index) => (
                  <motion.div
                    key={agent.agent_id || index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow cursor-pointer"
                    onClick={() => handleChatWithAgent(agent.agent_id)}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <div className="text-3xl">
                          {getAgentIcon(agent.agent_id)}
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900">
                            {agent.name}
                          </h3>
                          <p className="text-sm text-gray-500 capitalize">
                            AI Agent
                          </p>
                        </div>
                      </div>
                    </div>

                    <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                      {agent.description || 'No description available'}
                    </p>


                    {/* Simple @ tag link */}
                    <div className="mt-auto pt-4 border-t border-gray-100">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleChatWithAgent(agent.agent_id)
                        }}
                        className="text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
                      >
                        @{agent.name.toLowerCase().replace(/\s+/g, '-')}
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="mt-8 text-center text-sm text-gray-500">
            <div className="flex items-center justify-center space-x-2">
              <SparklesIcon className="w-4 h-4" />
              <span>💡 Tip: Click on any agent to start a conversation or ask about their capabilities</span>
            </div>
          </div>
        </div>
      </div>

      {/* Chat Input Area - Always at bottom */}
      <FilesChatInput />
    </div>
  )
}

export default AgentsPage
