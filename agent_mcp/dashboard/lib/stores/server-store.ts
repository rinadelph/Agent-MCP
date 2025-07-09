import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { apiClient } from '../api'
import { config, getAutoDetectServers } from '../config'

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
  autoDetectServers: () => Promise<MCPServer | null>
  clearPersistedData: () => void
}

export const useServerStore = create<ServerStore>()(
  persist(
    (set, get) => ({
      servers: [],
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
          // Use debug logging for health check failures (common during server discovery)
          console.debug(`Health check failed for server ${id}`)
          return false
        }
      },

      refreshAllServers: async () => {
        const servers = get().servers
        
        // Enable error suppression during bulk health checks
        apiClient.setSuppressErrors(true)
        
        const healthPromises = servers.map(async (server) => {
          const isHealthy = await get().checkServerHealth(server.id)
          return {
            id: server.id,
            status: isHealthy ? 'connected' : 'disconnected'
          }
        })

        const results = await Promise.all(healthPromises)
        
        // Disable error suppression after checks
        apiClient.setSuppressErrors(false)
        
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
      },

      autoDetectServers: async () => {
        const possibleServers = getAutoDetectServers()
        
        // Enable error suppression during auto-detection
        apiClient.setSuppressErrors(true)
        
        for (const serverConfig of possibleServers) {
          try {
            // Temporarily set API client to test this server
            apiClient.setServer(serverConfig.host, serverConfig.port)
            
            const response = await apiClient.getSystemStatus()
            
            if (response.server_running === true) {
              // Found a working server
              const detectedServer: MCPServer = {
                id: `auto_${serverConfig.port}`,
                name: `Auto-detected (${serverConfig.host}:${serverConfig.port})`,
                host: serverConfig.host,
                port: serverConfig.port,
                status: 'connected',
                lastConnected: new Date().toISOString(),
                description: 'Automatically detected MCP server'
              }
              
              // Add to servers list if not already present
              const existingServer = get().servers.find(
                s => s.host === serverConfig.host && s.port === serverConfig.port
              )
              
              if (!existingServer) {
                set((state) => ({
                  servers: [...state.servers, detectedServer]
                }))
              } else {
                // Update existing server status
                set((state) => ({
                  servers: state.servers.map(s => 
                    s.id === existingServer.id 
                      ? { ...s, status: 'connected', lastConnected: new Date().toISOString() }
                      : s
                  )
                }))
              }
              
              return existingServer || detectedServer
            }
          } catch (error) {
            // Continue to next port
            console.debug(`Server not found on ${serverConfig.host}:${serverConfig.port}`)
          }
        }
        
        // Disable error suppression after auto-detection
        apiClient.setSuppressErrors(false)
        
        // No server found
        return null
      },

      clearPersistedData: () => {
        // Reset to default state
        set({
          servers: [],
          activeServerId: null,
          isConnecting: false,
          connectionError: null
        })
        
        // Clear localStorage
        if (typeof window !== 'undefined') {
          localStorage.removeItem('mcp-server-store')
        }
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