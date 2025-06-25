import { create } from 'zustand'
import { Agent, Task, apiClient } from '../api'

// Memoization cache for expensive computations
const memoCache = new Map<string, { data: any, timestamp: number }>()
const CACHE_DURATION = 5000 // 5 seconds cache

function memoize<T>(key: string, computation: () => T): T {
  const cached = memoCache.get(key)
  const now = Date.now()
  
  if (cached && now - cached.timestamp < CACHE_DURATION) {
    return cached.data as T
  }
  
  const result = computation()
  memoCache.set(key, { data: result, timestamp: now })
  return result
}

function clearMemoCache() {
  memoCache.clear()
}

// Debounce utility for API calls
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null
  
  return (...args: Parameters<T>) => {
    if (timeout) {
      clearTimeout(timeout)
    }
    
    timeout = setTimeout(() => {
      func(...args)
    }, wait)
  }
}

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
  getAgentTaskAnalysis: (agentId: string) => {
    assignedTasks: Task[]
    workedOnTasks: Task[]
    completedTasks: Task[]
    completionActions: any[]
    totalTasks: number
    assignedCount: number
    workedOnCount: number
    completedCount: number
    completionActionCount: number
  }
  updateAgent: (agent: Agent) => void
  updateTask: (task: Task) => void
  refreshData: () => Promise<void>
  shouldDisplayAgent: (agent: any) => boolean
  getActiveAgents: () => any[]
  getIdleAgentsForCleanup: () => any[]
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
        console.log('🔍 All-data endpoint error:', err)
        
        const [agents, tasks, tokens] = await Promise.all([
          apiClient.getAgents(),
          apiClient.getTasks(),
          apiClient.getTokens()
        ])
        
        // Try to get context data separately
        let contextData = []
        try {
          const contextResponse = await fetch(`${apiClient.getServerUrl()}/api/all-data`)
          if (contextResponse.ok) {
            const fullData = await contextResponse.json()
            contextData = fullData.context || []
          }
        } catch (contextErr) {
          console.log('⚠️ Could not fetch context data in fallback:', contextErr)
          console.log('🔍 Server URL:', apiClient.getServerUrl())
        }
        
        // Merge tokens into agents
        const agentsWithTokens = agents.map(agent => {
          const token = tokens.agent_tokens.find(t => t.agent_id === agent.agent_id)?.token ||
                        (agent.agent_id === 'Admin' ? tokens.admin_token : undefined)
          return { ...agent, auth_token: token }
        })
        
        data = {
          agents: agentsWithTokens,
          tasks,
          context: contextData,
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
        context: data.context?.length || 0,
        actions: data.actions?.length || 0
      })
      console.log('🔍 Debug - Context data received:', data.context)
      
      // Clear memoization cache when data updates
      clearMemoCache()
      
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
    
    // Create cache key including data timestamp for cache invalidation
    const cacheKey = `agent-tasks-${agentId}-${state.data.timestamp}`
    
    return memoize(cacheKey, () => {
      // Strip prefix if present for consistent matching
      const cleanAgentId = agentId.startsWith('agent_') ? agentId.substring(6) : agentId
      // Handle admin variations - both 'Admin' and 'admin' are used in the system
      const normalizedAgentId = cleanAgentId === 'Admin' ? 'admin' : cleanAgentId
      
      // Get tasks assigned to this agent (handle both admin variations)
      const assignedTasks = state.data!.tasks.filter(t => 
        t.assigned_to === normalizedAgentId || 
        t.assigned_to === cleanAgentId ||
        (normalizedAgentId === 'admin' && (t.assigned_to === 'Admin' || t.assigned_to === 'admin'))
      )
      
      // Get tasks this agent has worked on (via actions)
      const workedOnTaskIds = new Set<string>()
      const agentActions = state.data!.actions.filter(a => 
        a.agent_id === normalizedAgentId || 
        a.agent_id === cleanAgentId ||
        (normalizedAgentId === 'admin' && (a.agent_id === 'Admin' || a.agent_id === 'admin'))
      )
      
      agentActions.forEach(action => {
        if (action.task_id) {
          workedOnTaskIds.add(action.task_id)
        }
      })
      
      // Get tasks worked on but not assigned
      const workedOnTasks = state.data!.tasks.filter(t => 
        workedOnTaskIds.has(t.task_id) && 
        t.assigned_to !== normalizedAgentId && 
        t.assigned_to !== cleanAgentId &&
        !(normalizedAgentId === 'admin' && (t.assigned_to === 'Admin' || t.assigned_to === 'admin'))
      )
      
      // Combine and deduplicate
      const allTasks = [...assignedTasks, ...workedOnTasks]
      const uniqueTasks = allTasks.filter((task, index, arr) => 
        arr.findIndex(t => t.task_id === task.task_id) === index
      )
      
      return uniqueTasks
    })
  },

  getAgentActions: (agentId: string) => {
    const state = get()
    if (!state.data) return []
    
    // Strip prefix if present for consistent matching
    const cleanAgentId = agentId.startsWith('agent_') ? agentId.substring(6) : agentId
    // Handle admin variations - both 'Admin' and 'admin' are used in the system
    const normalizedAgentId = cleanAgentId === 'Admin' ? 'admin' : cleanAgentId
    
    return state.data.actions.filter(a => 
      a.agent_id === normalizedAgentId || 
      a.agent_id === cleanAgentId ||
      (normalizedAgentId === 'admin' && (a.agent_id === 'Admin' || a.agent_id === 'admin'))
    )
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

  getAgentTaskAnalysis: (agentId: string) => {
    const state = get()
    if (!state.data) return {
      assignedTasks: [],
      workedOnTasks: [],
      completedTasks: [],
      completionActions: [],
      totalTasks: 0,
      assignedCount: 0,
      workedOnCount: 0,
      completedCount: 0,
      completionActionCount: 0
    }
    
    const cleanAgentId = agentId.startsWith('agent_') ? agentId.substring(6) : agentId
    // Handle admin variations
    const normalizedAgentId = cleanAgentId === 'Admin' ? 'admin' : cleanAgentId
    
    const allTasks = get().getAgentTasks(agentId)
    
    const assignedTasks = allTasks.filter(t => 
      t.assigned_to === normalizedAgentId || 
      t.assigned_to === cleanAgentId ||
      (normalizedAgentId === 'admin' && (t.assigned_to === 'Admin' || t.assigned_to === 'admin'))
    )
    const workedOnTasks = allTasks.filter(t => 
      t.assigned_to !== normalizedAgentId && 
      t.assigned_to !== cleanAgentId &&
      !(normalizedAgentId === 'admin' && (t.assigned_to === 'Admin' || t.assigned_to === 'admin'))
    )
    const completedTasks = allTasks.filter(t => t.status === 'completed')
    
    // Get completion actions for this agent
    const completionActions = state.data.actions.filter(a => 
      (a.agent_id === normalizedAgentId || a.agent_id === cleanAgentId) && 
      (a.action_type === 'task_completed' || a.action_type === 'complete_task' || a.action_type.includes('complet'))
    )
    
    
    return {
      assignedTasks,
      workedOnTasks,
      completedTasks,
      completionActions,
      totalTasks: allTasks.length,
      assignedCount: assignedTasks.length,
      workedOnCount: workedOnTasks.length,
      completedCount: completedTasks.length,
      completionActionCount: completionActions.length
    }
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
  },
  
  // Debounced refresh to prevent rapid successive calls
  debouncedRefresh: debounce(async () => {
    await get().fetchAllData()
  }, 500),

  // Agent lifecycle management
  shouldDisplayAgent: (agent: any) => {
    // Always show admin
    if (agent.agent_id === 'Admin' || agent.agent_id === 'admin') return true
    
    // Show if agent has an active task
    if (agent.current_task) return true
    
    // Show if agent is new (created within last 10 minutes)
    const now = new Date()
    const createdAt = new Date(agent.created_at)
    const ageInMinutes = (now.getTime() - createdAt.getTime()) / (1000 * 60)
    
    return ageInMinutes <= 10
  },

  getActiveAgents: () => {
    const state = get()
    if (!state.data) return []
    
    return state.data.agents.filter(agent => get().shouldDisplayAgent(agent))
  },

  getIdleAgentsForCleanup: () => {
    const state = get()
    if (!state.data) return []
    
    const now = new Date()
    return state.data.agents.filter(agent => {
      // Never cleanup admin
      if (agent.agent_id === 'Admin' || agent.agent_id === 'admin') return false
      
      // Don't cleanup if has active task
      if (agent.current_task) return false
      
      // Don't cleanup if already terminated
      if (agent.status === 'terminated') return false
      
      // Cleanup if older than 10 minutes without task
      const createdAt = new Date(agent.created_at)
      const ageInMinutes = (now.getTime() - createdAt.getTime()) / (1000 * 60)
      
      return ageInMinutes > 10
    })
  }
}))

// Auto-refresh every 60 seconds (reduced from 30s for better performance)
if (typeof window !== 'undefined') {
  setInterval(() => {
    const store = useDataStore.getState()
    if (store.data) {
      store.refreshData()
    }
  }, 60000)
}