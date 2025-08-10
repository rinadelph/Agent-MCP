"use client"

import React, { useEffect, useState } from "react"
import { Server, Wifi, WifiOff, Plus, RefreshCw, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useServerStore } from "@/lib/stores/server-store"
import { ProjectPicker } from "./project-picker"
import { ManualServerInput } from "./manual-server-input"
import { config } from "@/lib/config"

export function ServerConnection() {
  const { 
    servers, 
    activeServerId, 
    setActiveServer, 
    autoDetectServers, 
    clearPersistedData,
    removeServer,
    isConnecting 
  } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  const [isDetecting, setIsDetecting] = useState(false)

  const connectedServers = servers.filter(s => s.status === 'connected')
  const disconnectedServers = servers.filter(s => s.status !== 'connected')

  // Auto-detection is now manual - users need to click the button
  // useEffect(() => {
  //   if (config.autoDetect.enabled && !activeServerId && !isConnecting) {
  //     handleAutoDetect()
  //   }
  // }, [])

  const handleAutoDetect = async () => {
    setIsDetecting(true)
    try {
      const detectedServer = await autoDetectServers()
      if (detectedServer && config.autoDetect.enabled) {
        await setActiveServer(detectedServer.id)
      }
    } catch (error) {
      console.error('Auto-detection failed:', error)
    } finally {
      setIsDetecting(false)
    }
  }

  const handleClearData = () => {
    if (confirm('This will clear all saved server configurations and reset to defaults. Continue?')) {
      clearPersistedData()
    }
  }

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-[var(--space-fluid-xl)]">
      <div className="max-w-2xl w-full space-y-[var(--space-fluid-lg)]">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 bg-teal-500/20 rounded-full flex items-center justify-center">
            <Server className="w-8 h-8 text-teal-500" />
          </div>
          <div>
            <h2 className="text-fluid-2xl font-bold text-foreground">Connect to MCP Server</h2>
            <p className="text-muted-foreground text-fluid-base mt-2">
              Choose a server to start managing agents and tasks
            </p>
          </div>
        </div>

        {/* Connected Servers */}
        {connectedServers.length > 0 && (
          <div className="space-y-[var(--space-fluid-sm)]">
            <h3 className="text-fluid-sm font-medium text-foreground flex items-center gap-2">
              <Wifi className="w-4 h-4 text-green-500" />
              Connected Servers
            </h3>
            <div className="grid gap-[var(--space-fluid-sm)]">
              {connectedServers.map((server) => (
                <Card 
                  key={server.id} 
                  className={`cursor-pointer transition-all hover:shadow-md ${
                    activeServerId === server.id ? 'ring-2 ring-teal-500 bg-teal-50/50 dark:bg-teal-950/20' : ''
                  }`}
                  onClick={() => setActiveServer(server.id)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                        <div>
                          <h4 className="font-medium text-foreground">{server.name}</h4>
                          <p className="text-sm text-muted-foreground">
                            {server.host}:{server.port}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800">
                          Connected
                        </Badge>
                        {activeServerId === server.id && (
                          <Badge className="bg-teal-500 text-white">
                            Active
                          </Badge>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="opacity-50 hover:opacity-100 text-destructive hover:text-destructive"
                          onClick={(e) => {
                            e.stopPropagation()
                            if (confirm(`Delete server "${server.name}"?`)) {
                              removeServer(server.id)
                            }
                          }}
                        >
                          <Trash2 className="w-4 h-4" />
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
              Available Servers
            </h3>
            <div className="grid gap-3">
              {disconnectedServers.map((server) => (
                <Card 
                  key={server.id} 
                  className="cursor-pointer transition-all hover:shadow-md opacity-60"
                  onClick={() => setActiveServer(server.id)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-2 bg-orange-500 rounded-full" />
                        <div>
                          <h4 className="font-medium text-foreground">{server.name}</h4>
                          <p className="text-sm text-muted-foreground">
                            {server.host}:{server.port}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-300 dark:border-orange-800">
                          {server.status === 'connecting' ? 'Connecting...' : 'Disconnected'}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="opacity-50 hover:opacity-100 text-destructive hover:text-destructive"
                          onClick={(e) => {
                            e.stopPropagation()
                            if (confirm(`Delete server "${server.name}"?`)) {
                              removeServer(server.id)
                            }
                          }}
                        >
                          <Trash2 className="w-4 h-4" />
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
            <CardContent className="p-6">
              <ManualServerInput />
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        {connectedServers.length === 0 && (
          <div className="text-center pt-4 space-y-3">
            <p className="text-sm text-muted-foreground">
              No servers connected. Add a server above or check your connection settings.
            </p>
            <Button
              onClick={handleAutoDetect}
              disabled={isDetecting}
              variant="outline"
              className="gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${isDetecting ? 'animate-spin' : ''}`} />
              {isDetecting ? 'Searching...' : 'Auto-detect Servers'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}