import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { apiClient } from '../api'

export interface MCPServer {
  id: string
  name: string
  host: string
  port: number
  status: 'connected' | 'disconnected' | 'connecting' | 'error'
  lastConnected?: string
  description?: string
}

interface ServerStore {
  servers: MCPServer[]
  activeServerId: string | null
  isConnecting: boolean
  connectionError: string | null
  
  // Actions
  addServer: (server: Omit<MCPServer, 'id' | 'status'>) => void
  removeServer: (id: string) => void
  updateServer: (id: string, updates: Partial<MCPServer>) => void
  setActiveServer: (id: string) => Promise<void>
  checkServerHealth: (id: string) => Promise<boolean>
  refreshAllServers: () => Promise<void>
  disconnectServer: () => void
}

export const useServerStore = create<ServerStore>()(
  persist(
    (set, get) => ({
      servers: [
        {
          id: 'default',
          name: 'Local Development',
          host: 'localhost',
          port: 8080,
          status: 'disconnected',
          description: 'Default local MCP server'
        }
      ],
      activeServerId: null,
      isConnecting: false,
      connectionError: null,

      addServer: (serverData) => {
        const newServer: MCPServer = {
          ...serverData,
          id: `server_${Date.now()}`,
          status: 'disconnected'
        }
        
        set((state) => ({
          servers: [...state.servers, newServer]
        }))
      },

      removeServer: (id) => {
        set((state) => ({
          servers: state.servers.filter(s => s.id !== id),
          activeServerId: state.activeServerId === id ? null : state.activeServerId
        }))
      },

      updateServer: (id, updates) => {
        set((state) => ({
          servers: state.servers.map(s => 
            s.id === id ? { ...s, ...updates } : s
          )
        }))
      },

      setActiveServer: async (id) => {
        const server = get().servers.find(s => s.id === id)
        if (!server) return

        set({ isConnecting: true, connectionError: null })

        try {
          // Update API client to use this server
          apiClient.setServer(server.host, server.port)
          
          // Test connection
          const isHealthy = await get().checkServerHealth(id)
          
          if (isHealthy) {
            set((state) => ({
              activeServerId: id,
              isConnecting: false,
              servers: state.servers.map(s => ({
                ...s,
                status: s.id === id ? 'connected' : 'disconnected',
                lastConnected: s.id === id ? new Date().toISOString() : s.lastConnected
              }))
            }))
          } else {
            throw new Error('Server health check failed')
          }
        } catch (error) {
          set((state) => ({
            isConnecting: false,
            connectionError: error instanceof Error ? error.message : 'Connection failed',
            servers: state.servers.map(s => ({
              ...s,
              status: s.id === id ? 'error' : s.status
            }))
          }))
        }
      },

      checkServerHealth: async (id) => {
        try {
          const server = get().servers.find(s => s.id === id)
          if (!server) return false

          // Temporarily set API client to test this server
          const originalUrl = apiClient.getServerUrl()
          apiClient.setServer(server.host, server.port)
          
          const response = await apiClient.getSystemStatus()
          
          // Restore original URL if this was just a test
          if (get().activeServerId !== id) {
            const activeServer = get().servers.find(s => s.id === get().activeServerId)
            if (activeServer) {
              apiClient.setServer(activeServer.host, activeServer.port)
            }
          }
          
          return response.server_running === true
        } catch (error) {
          console.error(`Health check failed for server ${id}:`, error)
          return false
        }
      },

      refreshAllServers: async () => {
        const servers = get().servers
        const healthPromises = servers.map(async (server) => {
          const isHealthy = await get().checkServerHealth(server.id)
          return {
            id: server.id,
            status: isHealthy ? 'connected' : 'disconnected'
          }
        })

        const results = await Promise.all(healthPromises)
        
        set((state) => ({
          servers: state.servers.map(server => {
            const result = results.find(r => r.id === server.id)
            return result ? { ...server, status: result.status as MCPServer['status'] } : server
          })
        }))
      },

      disconnectServer: () => {
        set((state) => ({
          activeServerId: null,
          servers: state.servers.map(s => ({ ...s, status: 'disconnected' as const }))
        }))
        
        // Reset API client
        apiClient.setServer('', 0)
      }
    }),
    {
      name: 'mcp-server-store',
      partialize: (state) => ({
        servers: state.servers,
        activeServerId: state.activeServerId
      })
    }
  )
)