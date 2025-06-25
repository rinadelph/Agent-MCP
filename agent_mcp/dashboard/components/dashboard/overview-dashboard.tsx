"use client"

import React, { useState, useEffect } from "react"
import { Network, RefreshCw, Server } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { useServerStore } from "@/lib/stores/server-store"
import { useDataStore } from "@/lib/stores/data-store"
import { VisGraph } from "./vis-graph-simple"
import { NodeDetailPanel } from "./node-detail-panel"

export function OverviewDashboard() {
  const [mounted, setMounted] = useState(false)
  const { servers, activeServerId } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  const { data, loading, fetchAllData, isRefreshing } = useDataStore()
  
  // Selected node state for detail panel
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedNodeType, setSelectedNodeType] = useState<'agent' | 'task' | 'context' | 'file' | 'admin' | null>(null)
  const [selectedNodeData, setSelectedNodeData] = useState<any>(null)
  const [isPanelOpen, setIsPanelOpen] = useState(false)
  
  useEffect(() => {
    setMounted(true)
    // Fetch data on mount
    if (activeServerId && activeServer?.status === 'connected') {
      fetchAllData()
    }
  }, [activeServerId, activeServer?.status])
  
  const isConnected = !!activeServerId && activeServer?.status === 'connected'

  // Show connection prompt if no server is selected
  if (!isConnected) {
    return (
      <div className="h-full flex items-center justify-center p-4">
        <Card className="max-w-md">
          <CardContent className="flex flex-col items-center justify-center py-12 px-8 text-center">
            <Server className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">Connect to an MCP Server</h3>
            <p className="text-muted-foreground text-sm">
              Select an MCP server from the project picker in the header to view the system graph and manage agents.
            </p>
            {activeServer && activeServer.status === 'error' && (
              <div className="text-sm text-destructive mt-4">
                Failed to connect to {activeServer.name} ({activeServer.host}:{activeServer.port})
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  const handleClosePanel = () => {
    setIsPanelOpen(false)
    setSelectedNodeId(null)
    setSelectedNodeType(null)
    setSelectedNodeData(null)
  }

  return (
    <div className="w-full h-full flex flex-col" style={{
      paddingRight: isPanelOpen ? `calc(384px)` : '0px',
      transition: 'padding-right 0.5s ease-in-out'
    }}>
      {/* Minimal Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Network className="h-5 w-5 text-primary" />
          <h1 className="text-xl font-semibold">Multi-Agent Collaboration Network</h1>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/30">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse mr-2" />
            Connected to {activeServer?.name}
          </Badge>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => fetchAllData(true)}
            disabled={loading || isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 ${(loading || isRefreshing) ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Full Screen Graph Container */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <VisGraph 
          fullscreen 
          selectedNodeId={selectedNodeId}
          selectedNodeType={selectedNodeType}
          selectedNodeData={selectedNodeData}
          isPanelOpen={isPanelOpen}
          onNodeSelect={(nodeId, nodeType, nodeData) => {
            setSelectedNodeId(nodeId)
            setSelectedNodeType(nodeType)
            setSelectedNodeData(nodeData)
            setIsPanelOpen(true)
          }}
          onClosePanel={handleClosePanel}
        />
      </div>
      
      {/* Node Detail Panel - Fixed positioned like agents dashboard */}
      <NodeDetailPanel
        nodeId={selectedNodeId}
        nodeType={selectedNodeType}
        nodeData={selectedNodeData}
        isOpen={isPanelOpen}
        onClose={handleClosePanel}
      />
    </div>
  )
}