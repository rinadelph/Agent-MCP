import { create } from 'zustand'
import { Agent, Task, apiClient } from '../api'

interface AllData {
  agents: Agent[]
  tasks: Task[]
  context: any[]
  actions: any[]
  file_metadata: any[]
  file_map: Record<string, any>
  admin_token: string
  timestamp: string
}

interface DataStore {
  // Data
  data: AllData | null
  loading: boolean
  error: string | null
  lastFetch: number
  isRefreshing: boolean

  // Actions
  fetchAllData: (force?: boolean) => Promise<void>
  getAgent: (agentId: string) => Agent | undefined
  getAgentTasks: (agentId: string) => Task[]
  getAgentActions: (agentId: string) => any[]
  getTask: (taskId: string) => Task | undefined
  getContext: (contextKey: string) => any | undefined
  getAdminToken: () => string | undefined
  getAgentToken: (agentId: string) => string | undefined
  updateAgent: (agent: Agent) => void
  updateTask: (task: Task) => void
  refreshData: () => Promise<void>
}

export const useDataStore = create<DataStore>((set, get) => ({
  data: null,
  loading: false,
  error: null,
  lastFetch: 0,
  isRefreshing: false,

  fetchAllData: async (force = false) => {
    const state = get()
    
    // Skip if already loading
    if (state.loading || state.isRefreshing) return
    
    // Skip if data is fresh (less than 30 seconds old) unless forced
    const now = Date.now()
    if (!force && state.data && now - state.lastFetch < 30000) return
    
    // Set loading state appropriately
    if (!state.data || force) {
      set({ loading: true, error: null })
    } else {
      set({ isRefreshing: true, error: null })
    }
    
    try {
      // Try the new all-data endpoint first
      let data
      try {
        const response = await fetch(`${apiClient.getServerUrl()}/api/all-data`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          },
          mode: 'cors'
        })
        if (!response.ok) throw new Error(`Failed to fetch: ${response.statusText}`)
        data = await response.json()
      } catch (err) {
        // Fallback to fetching data from individual endpoints
        console.log('⚠️ All-data endpoint not available, using fallback...')
        
        const [agents, tasks, tokens] = await Promise.all([
          apiClient.getAgents(),
          apiClient.getTasks(),
          apiClient.getTokens()
        ])
        
        // Merge tokens into agents
        const agentsWithTokens = agents.map(agent => {
          const token = tokens.agent_tokens.find(t => t.agent_id === agent.agent_id)?.token ||
                        (agent.agent_id === 'Admin' ? tokens.admin_token : undefined)
          return { ...agent, auth_token: token }
        })
        
        data = {
          agents: agentsWithTokens,
          tasks,
          context: [],
          actions: [],
          file_metadata: [],
          file_map: {},
          admin_token: tokens.admin_token,
          timestamp: new Date().toISOString()
        }
      }
      
      console.log('✅ Fetched all data:', {
        agents: data.agents?.length || 0,
        tasks: data.tasks?.length || 0,
        actions: data.actions?.length || 0
      })
      
      set({ 
        data, 
        loading: false,
        isRefreshing: false, 
        error: null,
        lastFetch: now
      })
    } catch (error) {
      console.error('❌ Failed to fetch all data:', error)
      set({ 
        loading: false,
        isRefreshing: false, 
        error: error instanceof Error ? error.message : 'Failed to fetch data'
      })
    }
  },

  getAgent: (agentId: string) => {
    const state = get()
    if (!state.data) return undefined
    
    // Handle Admin specially
    if (agentId === 'Admin' || agentId === 'admin') {
      return state.data.agents.find(a => a.agent_id === 'Admin')
    }
    
    // Strip prefix if present
    const cleanId = agentId.startsWith('agent_') ? agentId.substring(6) : agentId
    return state.data.agents.find(a => a.agent_id === cleanId)
  },

  getAgentTasks: (agentId: string) => {
    const state = get()
    if (!state.data) return []
    return state.data.tasks.filter(t => t.assigned_to === agentId)
  },

  getAgentActions: (agentId: string) => {
    const state = get()
    if (!state.data) return []
    return state.data.actions.filter(a => a.agent_id === agentId)
  },

  getTask: (taskId: string) => {
    const state = get()
    if (!state.data) return undefined
    
    // Strip prefix if present
    const cleanId = taskId.startsWith('task_') ? taskId.substring(5) : taskId
    return state.data.tasks.find(t => t.task_id === cleanId)
  },

  getContext: (contextKey: string) => {
    const state = get()
    if (!state.data) return undefined
    
    // Strip prefix if present
    const cleanKey = contextKey.startsWith('context_') ? contextKey.substring(8) : contextKey
    return state.data.context.find(c => c.context_key === cleanKey)
  },

  getAdminToken: () => {
    const state = get()
    return state.data?.admin_token
  },

  getAgentToken: (agentId: string) => {
    const agent = get().getAgent(agentId)
    return agent?.auth_token
  },

  updateAgent: (agent: Agent) => {
    const state = get()
    if (!state.data) return
    
    const index = state.data.agents.findIndex(a => a.agent_id === agent.agent_id)
    if (index !== -1) {
      const newAgents = [...state.data.agents]
      newAgents[index] = agent
      set({
        data: {
          ...state.data,
          agents: newAgents
        }
      })
    }
  },

  updateTask: (task: Task) => {
    const state = get()
    if (!state.data) return
    
    const index = state.data.tasks.findIndex(t => t.task_id === task.task_id)
    if (index !== -1) {
      const newTasks = [...state.data.tasks]
      newTasks[index] = task
      set({
        data: {
          ...state.data,
          tasks: newTasks
        }
      })
    }
  },

  refreshData: async () => {
    // Force refresh
    await get().fetchAllData(true)
  }
}))

// Auto-refresh every 30 seconds
if (typeof window !== 'undefined') {
  setInterval(() => {
    const store = useDataStore.getState()
    if (store.data) {
      store.refreshData()
    }
  }, 30000)
}