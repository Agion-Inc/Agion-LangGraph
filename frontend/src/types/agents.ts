/**
 * Agent-Chat Frontend Types - Agent System
 * Type definitions for AI agents and orchestration
 */

export type AgentStatus = 'idle' | 'processing' | 'success' | 'error' | 'timeout'

export type AgentCapability =
  | 'data_analysis'
  | 'anomaly_detection'
  | 'brand_analysis'
  | 'performance_metrics'
  | 'trend_analysis'
  | 'recommendation'
  | 'report_generation'
  | 'data_validation'

export interface Agent {
  agent_id: string
  name: string
  description: string
  version: string
  capabilities: AgentCapability[]
  keywords: string[]
  required_files: string[]
  metrics: AgentMetrics
  is_busy?: boolean
}

export interface AgentMetrics {
  total_requests: number
  successful_requests: number
  failed_requests: number
  average_execution_time: number
  last_executed?: string
}

export interface AgentRequest {
  request_id: string
  user_query: string
  context: Record<string, any>
  files: string[]
  parameters: Record<string, any>
  priority: number
  timeout?: number
  created_at: string
}

export interface AgentResponse {
  request_id: string
  agent_id: string
  status: AgentStatus
  data: Record<string, any>
  message: string
  confidence: number
  execution_time: number
  next_suggestions: string[]
  error_details?: Record<string, any>
  metadata: Record<string, any>
  created_at: string
  completed_at?: string
}

export interface AgentDiscovery {
  query: string
  discovered_agents: string[]
  confidence_scores: Record<string, number>
}

export interface AgentState {
  agents: Agent[]
  activeAgents: string[]
  isLoading: boolean
  error: string | null
  systemStats: SystemStats | null
}

export interface SystemStats {
  total_agents: number
  busy_agents: number
  active_requests: number
  total_requests: number
  total_successful: number
  total_failed: number
  success_rate: number
  capabilities: AgentCapability[]
  last_updated: string
}

export interface AgentActions {
  loadAgents: () => Promise<void>
  discoverAgents: (query: string) => Promise<string[]>
  invokeAgent: (agentId: string, request: Omit<AgentRequest, 'request_id' | 'created_at'>) => Promise<AgentResponse>
  invokeBestAgent: (query: string, context?: Record<string, any>, files?: string[]) => Promise<AgentResponse>
  orchestrateMultiAgent: (query: string, context?: Record<string, any>, files?: string[], maxAgents?: number) => Promise<AgentResponse[]>
  getSystemStats: () => Promise<void>
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export type AgentStore = AgentState & AgentActions