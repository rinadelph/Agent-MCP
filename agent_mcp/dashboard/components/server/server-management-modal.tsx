"use client"

import React, { useState } from "react"
import { Server, Wifi, WifiOff, Plus, RefreshCw, Trash2, Settings } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useServerStore } from "@/lib/stores/server-store"
import { ManualServerInput } from "./manual-server-input"
import { config } from "@/lib/config"

export function ServerManagementModal() {
  const { 
    servers, 
    activeServerId, 
    setActiveServer, 
    autoDetectServers, 
    clearPersistedData,
    removeServer,
    refreshAllServers,
    isConnecting 
  } = useServerStore()
  
  const [isOpen, setIsOpen] = useState(false)
  const [isDetecting, setIsDetecting] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const connectedServers = servers.filter(s => s.status === 'connected')
  const disconnectedServers = servers.filter(s => s.status !== 'connected')

  const handleAutoDetect = async () => {
    setIsDetecting(true)
    try {
      const detectedServer = await autoDetectServers()
      if (detectedServer) {
        await setActiveServer(detectedServer.id)
      }
    } catch (error) {
      console.error('Auto-detection failed:', error)
    } finally {
      setIsDetecting(false)
    }
  }

  const handleRefreshAll = async () => {
    setIsRefreshing(true)
    try {
      await refreshAllServers()
    } catch (error) {
      console.error('Refresh failed:', error)
    } finally {
      setIsRefreshing(false)
    }
  }

  const handleClearData = () => {
    if (confirm('This will clear all saved server configurations. Continue?')) {
      clearPersistedData()
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-8 w-8 shrink-0">
          <Settings className="h-4 w-4" />
          <span className="sr-only">Server Management</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Server className="w-5 h-5" />
            Server Management
          </DialogTitle>
          <DialogDescription>
            Manage your MCP server connections and configurations
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="flex gap-2 flex-wrap">
            <Button
              onClick={handleAutoDetect}
              disabled={isDetecting}
              variant="outline"
              size="sm"
              className="gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${isDetecting ? 'animate-spin' : ''}`} />
              {isDetecting ? 'Searching...' : 'Auto-detect'}
            </Button>
            <Button
              onClick={handleRefreshAll}
              disabled={isRefreshing}
              variant="outline"
              size="sm"
              className="gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              {isRefreshing ? 'Refreshing...' : 'Refresh All'}
            </Button>
            <Button
              onClick={handleClearData}
              variant="outline"
              size="sm"
              className="gap-2 text-destructive hover:text-destructive"
            >
              <Trash2 className="w-4 h-4" />
              Clear All
            </Button>
          </div>

          {/* Connected Servers */}
          {connectedServers.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
                <Wifi className="w-4 h-4 text-green-500" />
                Connected Servers ({connectedServers.length})
              </h3>
              <div className="grid gap-2">
                {connectedServers.map((server) => (
                  <Card 
                    key={server.id} 
                    className={`cursor-pointer transition-all hover:shadow-md ${
                      activeServerId === server.id ? 'ring-2 ring-teal-500 bg-teal-50/50 dark:bg-teal-950/20' : ''
                    }`}
                    onClick={() => setActiveServer(server.id)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                          <div>
                            <h4 className="font-medium text-sm">{server.name}</h4>
                            <p className="text-xs text-muted-foreground">
                              {server.host}:{server.port}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800 text-xs">
                            Connected
                          </Badge>
                          {activeServerId === server.id && (
                            <Badge className="bg-teal-500 text-white text-xs">
                              Active
                            </Badge>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 opacity-50 hover:opacity-100 text-destructive hover:text-destructive"
                            onClick={(e) => {
                              e.stopPropagation()
                              if (confirm(`Delete server "${server.name}"?`)) {
                                removeServer(server.id)
                              }
                            }}
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Disconnected Servers */}
          {disconnectedServers.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
                <WifiOff className="w-4 h-4 text-orange-500" />
                Available Servers ({disconnectedServers.length})
              </h3>
              <div className="grid gap-2">
                {disconnectedServers.map((server) => (
                  <Card 
                    key={server.id} 
                    className="cursor-pointer transition-all hover:shadow-md opacity-60"
                    onClick={() => setActiveServer(server.id)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-orange-500 rounded-full" />
                          <div>
                            <h4 className="font-medium text-sm">{server.name}</h4>
                            <p className="text-xs text-muted-foreground">
                              {server.host}:{server.port}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-300 dark:border-orange-800 text-xs">
                            {server.status === 'connecting' ? 'Connecting...' : 'Disconnected'}
                          </Badge>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 opacity-50 hover:opacity-100 text-destructive hover:text-destructive"
                            onClick={(e) => {
                              e.stopPropagation()
                              if (confirm(`Delete server "${server.name}"?`)) {
                                removeServer(server.id)
                              }
                            }}
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Add New Server */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
              <Plus className="w-4 h-4 text-blue-500" />
              Add New Server
            </h3>
            <Card className="border-dashed border-2 border-muted-foreground/20 hover:border-muted-foreground/40 transition-colors">
              <CardContent className="p-4">
                <ManualServerInput />
              </CardContent>
            </Card>
          </div>

          {/* Empty State */}
          {servers.length === 0 && (
            <div className="text-center py-8">
              <Server className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">
                No servers configured. Add a server above or use auto-detection.
              </p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}