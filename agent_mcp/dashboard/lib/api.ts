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
  type: 'agent' | 'task' | 'context' | 'file' | 'admin'
  status?: string
  metadata?: Record<string, unknown>
}

export interface GraphEdge {
  id: string
  from: string
  to: string
  type: string
  label?: string
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

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl
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
    const url = `${this.baseUrl}/api${endpoint}`
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`)
    }

    return response.json()
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

  // Node details endpoint
  async getNodeDetails(nodeId: string): Promise<{
    node_type: string
    details: Record<string, unknown>
  }> {
    return this.request(`/node-details/${nodeId}`)
  }

  // Real-time updates via Server-Sent Events
  createEventSource(endpoint: string): EventSource {
    return new EventSource(`${this.baseUrl}/api${endpoint}`)
  }

  // Utility methods
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.request('/health')
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