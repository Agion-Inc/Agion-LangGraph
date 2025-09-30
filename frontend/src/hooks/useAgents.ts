/**
 * Agent-Chat useAgents Hook
 * Zustand store for agent orchestration with latest APIs
 */

import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { nanoid } from 'nanoid'
import type { AgentStore, Agent, AgentRequest, AgentResponse } from '../types/agents'
import { apiClient } from '../services/api'

export const useAgentStore = create<AgentStore>()(
  subscribeWithSelector((set, get) => ({
    // State
    agents: [],
    activeAgents: [],
    isLoading: false,
    error: null,
    systemStats: null,

    // Actions
    loadAgents: async () => {
      set({ isLoading: true, error: null })

      try {
        const response = await apiClient.get<any>('/api/v1/agents')
        console.log('Agents API raw response:', response)
        
        // Handle different response formats from the backend
        let agents: Agent[] = []
        
        if (response && response.agents && Array.isArray(response.agents)) {
          // Standard format: { status: "success", agents: [...] }
          agents = response.agents
        } else if (Array.isArray(response)) {
          // Direct array response
          agents = response
        } else if (response && response.data && Array.isArray(response.data)) {
          // Wrapped in data: { data: [...] }
          agents = response.data
        }
        
        // Map backend agent format to frontend Agent type if needed
        agents = agents.map((agent: any) => ({
          agent_id: agent.agent_id || agent.id,
          name: agent.name || 'Unknown Agent',
          description: agent.description || '',
          version: agent.version || '1.0.0',
          capabilities: agent.capabilities || [],
          keywords: agent.keywords || [],
          required_files: agent.required_files || [],
          metrics: agent.metrics || {
            total_requests: 0,
            successful_requests: 0,
            failed_requests: 0,
            average_execution_time: 0
          },
          is_busy: agent.is_busy || false
        }))
        
        console.log('Processed agents for UI:', agents)
        set({ agents, isLoading: false })
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to load agents'
        console.error('Failed to load agents:', error)
        set({ error: errorMessage, isLoading: false, agents: [] })
        // Don't throw - allow the app to continue with no agents
      }
    },

    discoverAgents: async (query: string) => {
      set({ isLoading: true, error: null })

      try {
        const response = await apiClient.post<any>('/api/v1/agents/discover', {
          query,
          limit: 5,
        })
        console.log('Agent discovery response:', response)
        
        const agent_ids = response.agent_ids || response.data?.agent_ids || []
        set({ isLoading: false })
        return agent_ids
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to discover agents'
        console.error('Failed to discover agents:', error)
        set({ error: errorMessage, isLoading: false })
        return []
      }
    },

    invokeAgent: async (agentId: string, request: Omit<AgentRequest, 'request_id' | 'created_at'>) => {
      const fullRequest: AgentRequest = {
        ...request,
        request_id: nanoid(),
        created_at: new Date().toISOString(),
      }

      try {
        console.log('Invoking agent:', agentId, 'with request:', fullRequest)
        const response = await apiClient.post<AgentResponse>(`/api/v1/agents/${agentId}/invoke`, fullRequest)
        console.log('Agent response:', response)
        return response
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to invoke agent'
        console.error('Failed to invoke agent:', error)
        throw new Error(errorMessage)
      }
    },

    invokeBestAgent: async (query: string, context = {}, files = []) => {
      try {
        const request = {
          user_query: query,
          context,
          files,
          parameters: {},
          priority: 1,
        }

        console.log('Invoking best agent with:', request)
        const response = await apiClient.post<AgentResponse>('/api/v1/agents/invoke-best', request)
        console.log('Best agent response:', response)
        return response
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to invoke best agent'
        console.error('Failed to invoke best agent:', error)
        throw new Error(errorMessage)
      }
    },

    orchestrateMultiAgent: async (query: string, context = {}, files = [], maxAgents = 3) => {
      try {
        const request = {
          user_query: query,
          context,
          files,
          parameters: {},
          priority: 1,
          max_agents: maxAgents,
        }

        console.log('Orchestrating agents with:', request)
        const response = await apiClient.post<AgentResponse[]>('/api/v1/agents/orchestrate', request)
        console.log('Orchestration response:', response)
        return response
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to orchestrate agents'
        console.error('Failed to orchestrate agents:', error)
        throw new Error(errorMessage)
      }
    },

    getSystemStats: async () => {
      set({ isLoading: true, error: null })

      try {
        const stats = await apiClient.get('/api/v1/agents/stats')
        console.log('System stats:', stats)
        set({ systemStats: stats as any, isLoading: false })
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to get system stats'
        console.error('Failed to get system stats:', error)
        set({ error: errorMessage, isLoading: false })
        // Don't throw
      }
    },

    setLoading: (loading: boolean) => {
      set({ isLoading: loading })
    },

    setError: (error: string | null) => {
      set({ error })
    },
  }))
)

// Auto-load agents on first mount with retry
let hasAutoLoaded = false
let retryCount = 0
const maxRetries = 3

const loadAgentsWithRetry = async () => {
  try {
    await useAgentStore.getState().loadAgents()
    const agents = useAgentStore.getState().agents
    if (agents && agents.length > 0) {
      console.log(`Successfully loaded ${agents.length} agents`)
    } else if (retryCount < maxRetries) {
      retryCount++
      console.log(`No agents loaded, retrying... (attempt ${retryCount}/${maxRetries})`)
      setTimeout(loadAgentsWithRetry, 2000) // Retry after 2 seconds
    }
  } catch (error) {
    if (retryCount < maxRetries) {
      retryCount++
      console.log(`Failed to load agents, retrying... (attempt ${retryCount}/${maxRetries})`)
      setTimeout(loadAgentsWithRetry, 2000) // Retry after 2 seconds
    }
  }
}

useAgentStore.subscribe(
  state => state.agents.length,
  () => {
    if (!hasAutoLoaded) {
      hasAutoLoaded = true
      loadAgentsWithRetry()
    }
  },
  {
    fireImmediately: true,
  }
)
