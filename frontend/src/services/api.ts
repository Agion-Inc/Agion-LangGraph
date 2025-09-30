/**
 * Agent-Chat API Client
 * Modern fetch-based API client with TypeScript support
 */

class ApiClient {
  private baseURL: string
  private defaultHeaders: Record<string, string>

  constructor(baseURL: string = process.env.REACT_APP_API_URL !== undefined ? process.env.REACT_APP_API_URL : 'http://localhost:8000') {
    this.baseURL = baseURL
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    // Don't include default Content-Type header for FormData requests
    const headers = options.body instanceof FormData
      ? { ...options.headers }  // Don't include default headers for FormData
      : { ...this.defaultHeaders, ...options.headers }

    const config: RequestInit = {
      ...options,
      headers,
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        const error: any = new Error(
          errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`
        )
        error.response = { status: response.status }
        throw error
      }

      // Handle empty responses
      if (response.status === 204 || response.headers.get('content-length') === '0') {
        return {} as T
      }

      return await response.json()
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Network error: Unable to connect to the server')
      }
      throw error
    }
  }

  async get<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
    // Handle both absolute and relative URLs
    let finalUrl = endpoint
    
    if (params) {
      const urlParams = new URLSearchParams(params)
      finalUrl = `${endpoint}${endpoint.includes('?') ? '&' : '?'}${urlParams.toString()}`
    }

    return this.request<T>(finalUrl)
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async patch<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
    })
  }

  async uploadFile<T>(endpoint: string, file: File, additionalData?: Record<string, unknown>): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, JSON.stringify(value))
      })
    }

    return this.request<T>(endpoint, {
      method: 'POST',
      body: formData,
      headers: {
        // Don't set Content-Type for FormData - browser will set it with boundary
      },
    })
  }

  async uploadFiles<T>(endpoint: string, files: File[], additionalData?: Record<string, unknown>): Promise<T> {
    const formData = new FormData()

    files.forEach(file => {
      formData.append('files', file)
    })

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        // Handle different data types properly for form fields
        if (typeof value === 'boolean') {
          formData.append(key, value.toString())
        } else if (typeof value === 'string' || typeof value === 'number') {
          formData.append(key, value.toString())
        } else {
          formData.append(key, JSON.stringify(value))
        }
      })
    }

    return this.request<T>(endpoint, {
      method: 'POST',
      body: formData,
      headers: {
        // Don't set Content-Type for FormData
      },
    })
  }

  setAuthToken(token: string) {
    this.defaultHeaders['Authorization'] = `Bearer ${token}`
  }

  removeAuthToken() {
    delete this.defaultHeaders['Authorization']
  }

  setBaseURL(baseURL: string) {
    this.baseURL = baseURL
  }
}

export const apiClient = new ApiClient()

// Export types for API responses
export interface ApiError {
  detail: string
  type?: string
  code?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

// Chat History API
export interface ChatSessionResponse {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessageResponse {
  id: string
  role: string
  content: string
  agent_id?: string
  metadata?: any
  timestamp: string
}

export interface SessionListResponse {
  sessions: ChatSessionResponse[]
  total: number
  page: number
  per_page: number
}

export interface MessageListResponse {
  messages: ChatMessageResponse[]
  total: number
  page: number
  per_page: number
}

export interface ChatSendRequest {
  message: string
  session_id?: string
  context?: Record<string, any>
  files?: string[]
}

export interface ChatSendResponse {
  message: {
    role: string
    content: string
    timestamp: string
    agent_id?: string
    metadata?: Record<string, any>
  }
  agent_used?: string
  confidence: number
  session_id: string
}

export const chatHistoryApi = {
  sendMessage: (data: ChatSendRequest) => {
    return apiClient.post<ChatSendResponse>('/api/v1/chat/send', data)
  },

  getSessions: (page: number = 1, perPage: number = 20) => {
    return apiClient.get<SessionListResponse>('/api/v1/chat/sessions', {
      page: page.toString(),
      per_page: perPage.toString()
    })
  },

  getSessionMessages: (sessionId: string, page: number = 1, perPage: number = 50) => {
    return apiClient.get<MessageListResponse>(`/api/v1/chat/sessions/${sessionId}/messages`, {
      page: page.toString(),
      per_page: perPage.toString()
    })
  },

  deleteSession: (sessionId: string) => {
    return apiClient.delete(`/api/v1/chat/sessions/${sessionId}`)
  }
}