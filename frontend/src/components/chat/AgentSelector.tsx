/**
 * Agent Selector Component
 * Allows users to tag and select specific agents
 */

import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDownIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { useAgentStore } from '../../hooks/useAgents'
import type { Agent } from '../../types/agents'

interface AgentSelectorProps {
  selectedAgent?: Agent | null
  onAgentSelect: (agent: Agent | null) => void
  className?: string
}

export const AgentSelector: React.FC<AgentSelectorProps> = ({
  selectedAgent,
  onAgentSelect,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)
  const { agents, loadAgents } = useAgentStore()

  // Load agents on mount
  useEffect(() => {
    if (agents.length === 0) {
      loadAgents()
    }
  }, [agents.length, loadAgents])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Filter agents based on search term
  const filteredAgents = agents.filter(agent =>
    agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    agent.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
    agent.keywords.some(keyword =>
      keyword.toLowerCase().includes(searchTerm.toLowerCase())
    )
  )

  const handleAgentSelect = (agent: Agent) => {
    onAgentSelect(agent)
    setIsOpen(false)
    setSearchTerm('')
  }

  const handleClearSelection = (e: React.MouseEvent) => {
    e.stopPropagation()
    onAgentSelect(null)
  }

  const getAgentInitial = (name: string) => {
    return name.charAt(0).toUpperCase()
  }

  const getAgentColor = (agentId: string) => {
    if (agentId.includes('brand')) return 'bg-chat-blue-50 border-chat-blue-200 text-chat-blue-700'
    if (agentId.includes('anomaly')) return 'bg-chat-purple-50 border-chat-purple-200 text-chat-purple-700'
    return 'bg-chat-gray-50 border-chat-gray-200 text-chat-gray-700'
  }

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Selector Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full px-2 py-1.5 border rounded-md hover:border-chat-gray-400 focus:outline-none focus:ring-1 focus:ring-chat-blue-500 focus:border-transparent transition-colors duration-200 flex items-center justify-between text-left ${
          selectedAgent
            ? `${getAgentColor(selectedAgent.agent_id)} border-current`
            : 'border-chat-gray-300 bg-white'
        }`}
      >
        <div className="flex items-center space-x-1.5 flex-1 min-w-0">
          {selectedAgent ? (
            <>
              <span className="text-xs font-medium truncate">{selectedAgent.name}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleClearSelection(e)
                }}
                className="p-0.5 rounded hover:bg-black hover:bg-opacity-10 transition-colors flex-shrink-0"
                title="Clear agent selection"
              >
                <XMarkIcon className="w-3 h-3" />
              </button>
            </>
          ) : (
            <span className="text-xs text-chat-gray-500">Select Agent</span>
          )}
        </div>
        <ChevronDownIcon
          className={`w-3 h-3 text-chat-gray-500 transition-transform duration-200 flex-shrink-0 ml-1 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="absolute bottom-full mb-1 w-full bg-white border border-chat-gray-300 rounded-lg shadow-lg z-50 max-h-80 overflow-hidden"
        >
            {/* Search */}
            <div className="p-3 border-b border-chat-gray-200">
              <input
                type="text"
                placeholder="Search agents..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-3 py-2 border border-chat-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-chat-blue-500 focus:border-transparent text-sm"
                autoFocus
              />
            </div>

            {/* Agent List */}
            <div className="max-h-60 overflow-y-auto">
              {/* Auto option */}
              <button
                onClick={() => {
                  onAgentSelect(null)
                  setIsOpen(false)
                  setSearchTerm('')
                }}
                className="w-full px-3 py-3 text-left hover:bg-chat-gray-50 transition-colors border-b border-chat-gray-100"
              >
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 rounded-full bg-chat-gray-100 flex items-center justify-center">
                    <span className="text-xs font-semibold text-chat-gray-600">A</span>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-chat-gray-900">Automatic Selection</div>
                    <div className="text-xs text-chat-gray-500">
                      Let the system choose the best agent
                    </div>
                  </div>
                </div>
              </button>

              {/* Agents */}
              {filteredAgents.map((agent) => (
                <button
                  key={agent.agent_id}
                  onClick={() => handleAgentSelect(agent)}
                  className="w-full px-3 py-3 text-left hover:bg-chat-gray-50 transition-colors border-b border-chat-gray-100 last:border-b-0"
                >
                  <div className="flex items-center space-x-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      agent.agent_id.includes('brand') ? 'bg-chat-blue-100' :
                      agent.agent_id.includes('anomaly') ? 'bg-chat-purple-100' :
                      'bg-chat-gray-100'
                    }`}>
                      <span className={`text-xs font-semibold ${
                        agent.agent_id.includes('brand') ? 'text-chat-blue-600' :
                        agent.agent_id.includes('anomaly') ? 'text-chat-purple-600' :
                        'text-chat-gray-600'
                      }`}>
                        {getAgentInitial(agent.name)}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-chat-gray-900 truncate">
                        {agent.name}
                      </div>
                      <div className="text-xs text-chat-gray-500 truncate">
                        {agent.description}
                      </div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {agent.capabilities.slice(0, 3).map((capability) => (
                          <span
                            key={capability}
                            className="px-2 py-0.5 text-xs bg-chat-gray-100 text-chat-gray-600 rounded"
                          >
                            {capability.replace('_', ' ')}
                          </span>
                        ))}
                        {agent.capabilities.length > 3 && (
                          <span className="px-2 py-0.5 text-xs text-chat-gray-500">
                            +{agent.capabilities.length - 3}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              ))}

              {filteredAgents.length === 0 && (
                <div className="px-3 py-6 text-center text-sm text-chat-gray-500">
                  No agents found matching "{searchTerm}"
                </div>
              )}
            </div>
          </motion.div>
        )}
    </div>
  )
}

export default AgentSelector