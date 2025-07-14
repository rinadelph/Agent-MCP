// API client for Agent-MCP backend

export interface Agent {
  agent_id: string
  status: 'pending' | 'running' | 'terminated' | 'failed'
  current_task?: string
  working_directory?: string
  color?: string
  capabilities?: string[]
  created_at: string
  updated_at: string
  auth_token?: string
}

export interface Task {
  task_id: string
  title: string
  description?: string
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled' | 'failed'
  priority: 'low' | 'medium' | 'high'
  assigned_to?: string
  parent_task?: string
  child_tasks?: string[]
  depends_on_tasks?: string[]
  notes?: Array<{
    timestamp: string
    author: string
    content: string
  }>
  created_at: string
  updated_at: string
}

export interface GraphNode {
  id: string
  label: string
  group?: 'agent' | 'task' | 'context' | 'file' | 'admin'
  type?: 'agent' | 'task' | 'context' | 'file' | 'admin'
  status?: string
  priority?: string
  assigned_to?: string
  current_task?: string
  metadata?: Record<string, unknown>
  [key: string]: unknown
}

export interface GraphEdge {
  id?: string
  from: string
  to: string
  type?: string
  title?: string
  label?: string
  [key: string]: unknown
}

export interface Memory {
  context_key: string
  value: any
  description?: string
  last_updated: string
  updated_by: string
  _metadata?: {
    size_bytes: number
    size_kb: number
    json_valid: boolean
    days_old?: number
    is_stale: boolean
    is_large: boolean
  }
}

export interface MemoryHealthAnalysis {
  status: 'excellent' | 'good' | 'needs_attention' | 'critical' | 'no_data'
  health_score: number
  total: number
  stale_entries: number
  json_errors: number
  large_entries: number
  issues: string[]
  warnings: string[]
  recommendations: string[]
}

export interface SystemStatus {
  server_running: boolean
  total_agents: number
  active_agents: number
  total_tasks: number
  pending_tasks: number
  completed_tasks: number
  last_updated: string
}

export interface AgentDetails {
  agent: Agent
  token?: string
  tasks?: Task[]
  actions?: Array<{
    timestamp: string
    action_type: string
    task_id?: string
    details?: any
  }>
}

class ApiClient {
  private baseUrl: string
  private suppressErrors: boolean = false

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl
  }
  
  // Set whether to suppress connection errors (useful during server discovery)
  setSuppressErrors(suppress: boolean) {
    this.suppressErrors = suppress
  }

  // Dynamic server connection
  setServer(host: string, port: number) {
    this.baseUrl = `http://${host}:${port}`
  }

  getServerUrl(): string {
    return this.baseUrl
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    // Check if a server is connected
    if (!this.baseUrl) {
      throw new Error('NO_SERVER_CONNECTED')
    }
    
    const url = `${this.baseUrl}/api${endpoint}`
    
    // Enhanced CORS configuration
    const fetchOptions: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        // Don't set Origin header - let browser handle it automatically
        ...options.headers,
      },
      credentials: 'omit', // Don't include credentials for CORS
      mode: 'cors', // Explicitly set CORS mode
      cache: 'no-cache', // Always get fresh data
      ...options,
    }

    // Add timeout support
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout
    
    try {
      const response = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error')
        // Only log non-404 and non-405 errors (405 = Method Not Allowed, expected for some endpoints)
        if (response.status !== 404 && response.status !== 405) {
          console.error(`API Error [${response.status}]:`, errorText)
        }
        throw new Error(`API Error: ${response.status} ${response.statusText}`)
      }
      
      return await response.json()
    } catch (error) {
      clearTimeout(timeoutId)
      
      // Log errors only in debug mode or for non-connection errors
      if (error instanceof Error) {
        // Only log non-connection errors to console when not suppressing
        if (!this.suppressErrors && !error.message.includes('Failed to fetch') && !error.message.includes('ERR_CONNECTION_REFUSED')) {
          console.error(`Request failed to ${url}:`, {
            name: error.name,
            message: error.message,
            stack: error.stack
          })
        }
        
        if (error.name === 'AbortError') {
          throw new Error('Request timeout')
        }
        
        if (error.message.includes('Failed to fetch')) {
          // Throw a clean error without triggering additional console logs
          const err = new Error(`Network error: Unable to connect to ${this.baseUrl}`)
          // Mark this error as expected to prevent logging
          ;(err as any).isExpected = true
          throw err
        }
      }
      
      throw error
    }
  }

  // System endpoints
  async getSystemStatus(): Promise<SystemStatus> {
    return this.request<SystemStatus>('/status')
  }

  async getGraphData(): Promise<{ nodes: GraphNode[], edges: GraphEdge[] }> {
    return this.request<{ nodes: GraphNode[], edges: GraphEdge[] }>('/graph-data')
  }

  async getTaskTreeData(): Promise<{ nodes: GraphNode[], edges: GraphEdge[] }> {
    return this.request<{ nodes: GraphNode[], edges: GraphEdge[] }>('/task-tree-data')
  }

  // Agent endpoints
  async getAgents(): Promise<Agent[]> {
    return this.request<Agent[]>('/agents')
  }

  async getAgent(agentId: string): Promise<Agent> {
    return this.request<Agent>(`/agents/${agentId}`)
  }

  async getAgentDetails(agentId: string): Promise<AgentDetails> {
    // Get agent basic info
    const agent = await this.getAgent(agentId)
    
    // Get tokens
    const tokens = await this.getTokens()
    const agentToken = tokens.agent_tokens.find(t => t.agent_id === agentId)?.token || 
                       (agentId === 'Admin' ? tokens.admin_token : undefined)
    
    // Get node details which includes actions and related tasks
    const nodeDetails = await this.getNodeDetails(`agent_${agentId}`)
    
    return {
      agent: { ...agent, auth_token: agentToken },
      token: agentToken,
      tasks: (nodeDetails.related?.assigned_tasks as Task[]) || [],
      actions: (nodeDetails.actions as any[]) || []
    }
  }

  async createAgent(data: {
    agent_id: string
    capabilities?: string[]
    working_directory?: string
  }): Promise<{ success: boolean; message: string }> {
    return this.request('/agents', {
      method: 'POST',
      body: JSON.stringify(data)
    })
  }

  async terminateAgent(agentId: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/agents/${agentId}/terminate`, {
      method: 'POST'
    })
  }

  // Task endpoints
  async getTasks(): Promise<Task[]> {
    return this.request<Task[]>('/tasks')
  }

  async getTask(taskId: string): Promise<Task> {
    return this.request<Task>(`/tasks/${taskId}`)
  }

  async updateTask(taskId: string, data: Partial<Task>): Promise<{ success: boolean; message: string }> {
    return this.request(`/tasks/${taskId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    })
  }

  async createTask(data: {
    title: string
    description?: string
    priority?: 'low' | 'medium' | 'high'
    assigned_to?: string
    parent_task?: string
  }): Promise<{ success: boolean; message: string; task_id?: string }> {
    return this.request('/tasks', {
      method: 'POST',
      body: JSON.stringify(data)
    })
  }

  // Token endpoints
  async getTokens(): Promise<{
    admin_token: string
    agent_tokens: Array<{ agent_id: string; token: string }>
  }> {
    return this.request('/tokens')
  }

  // All data endpoint for caching
  async getAllData(): Promise<{
    agents: Agent[]
    tasks: Task[]
    context: any[]
    actions: any[]
    file_metadata: any[]
    file_map: Record<string, any>
    admin_token: string
    timestamp: string
  }> {
    return this.request('/all-data')
  }

  // Node details endpoint
  async getNodeDetails(nodeId: string): Promise<{
    id: string
    type: string
    data: Record<string, unknown>
    actions: Array<Record<string, unknown>>
    related?: Record<string, unknown>
  }> {
    return this.request(`/node-details?node_id=${encodeURIComponent(nodeId)}`)
  }

  // Memory endpoints
  async getMemories(options?: {
    context_key?: string
    search_query?: string
    show_health_analysis?: boolean
    show_stale_entries?: boolean
    max_results?: number
    sort_by?: 'key' | 'last_updated' | 'size'
  }): Promise<Memory[]> {
    // Note: This would require implementing MCP tool calls via the backend
    // For now, we'll use the context data from getAllData
    const allData = await this.getAllData()
    return allData.context.map(ctx => ({
      context_key: ctx.context_key,
      value: ctx.value,
      description: ctx.description,
      last_updated: ctx.last_updated,
      updated_by: ctx.updated_by,
      _metadata: {
        size_bytes: JSON.stringify(ctx.value).length,
        size_kb: Math.round(JSON.stringify(ctx.value).length / 1024 * 100) / 100,
        json_valid: true,
        days_old: ctx.last_updated ? Math.floor((Date.now() - new Date(ctx.last_updated).getTime()) / (1000 * 60 * 60 * 24)) : undefined,
        is_stale: ctx.last_updated ? (Date.now() - new Date(ctx.last_updated).getTime()) > (30 * 24 * 60 * 60 * 1000) : false,
        is_large: JSON.stringify(ctx.value).length > 10240
      }
    }))
  }

  async createMemory(data: {
    context_key: string
    context_value: any
    description?: string
    token: string
  }): Promise<{ success: boolean; message: string }> {
    // This would need to be implemented as an MCP tool call
    return this.request('/memories', {
      method: 'POST',
      body: JSON.stringify(data)
    })
  }

  async updateMemory(context_key: string, data: {
    context_value: any
    description?: string
    token: string
  }): Promise<{ success: boolean; message: string }> {
    // This would need to be implemented as an MCP tool call
    return this.request(`/memories/${encodeURIComponent(context_key)}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    })
  }

  async deleteMemory(context_key: string, token: string): Promise<{ success: boolean; message: string }> {
    // This would need to be implemented as an MCP tool call
    return this.request(`/memories/${encodeURIComponent(context_key)}`, {
      method: 'DELETE',
      body: JSON.stringify({ token })
    })
  }

  async getMemoryHealth(token: string): Promise<MemoryHealthAnalysis> {
    // This would need to be implemented as an MCP tool call
    return this.request('/memories/health', {
      method: 'POST',
      body: JSON.stringify({ token, show_health_analysis: true })
    })
  }

  // Real-time updates via Server-Sent Events
  createEventSource(endpoint: string): EventSource {
    return new EventSource(`${this.baseUrl}/api${endpoint}`)
  }

  // Utility methods
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.request('/health')
  }

  // CORS diagnostic method
  async testCORS(): Promise<boolean> {
    try {
      console.log(`Testing CORS connection to: ${this.baseUrl}`)
      
      // Try a simple OPTIONS request first
      const optionsResponse = await fetch(`${this.baseUrl}/api/health`, {
        method: 'OPTIONS',
        headers: {
          'Access-Control-Request-Method': 'GET',
          'Access-Control-Request-Headers': 'Content-Type'
        }
      })
      
      console.log('OPTIONS preflight response:', {
        status: optionsResponse.status,
        headers: Object.fromEntries(optionsResponse.headers.entries())
      })
      
      // Try the actual health check
      const healthResponse = await this.healthCheck()
      console.log('Health check successful:', healthResponse)
      
      return true
    } catch (error) {
      console.error('CORS test failed:', error)
      return false
    }
  }
}

// Create singleton instance
export const apiClient = new ApiClient()

// React Query keys
export const queryKeys = {
  systemStatus: ['system', 'status'] as const,
  graphData: ['graph', 'data'] as const,
  taskTreeData: ['task-tree', 'data'] as const,
  agents: ['agents'] as const,
  agent: (id: string) => ['agents', id] as const,
  tasks: ['tasks'] as const,
  task: (id: string) => ['tasks', id] as const,
  memories: ['memories'] as const,
  memory: (key: string) => ['memories', key] as const,
  memoryHealth: ['memories', 'health'] as const,
  tokens: ['tokens'] as const,
  nodeDetails: (id: string) => ['node-details', id] as const,
} as const

// Custom hooks for data fetching
export function usePolling(intervalMs: number = 10000) {
  return {
    refetchInterval: intervalMs,
    refetchIntervalInBackground: true,
    staleTime: intervalMs / 2,
  }
}