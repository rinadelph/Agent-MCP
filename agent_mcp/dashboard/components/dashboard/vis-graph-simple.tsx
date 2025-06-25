"use client"

import React from 'react'
import dynamic from 'next/dynamic'

// Dynamic import for heavy vis-network library
const VisNetworkComponent = dynamic(() => import('./vis-network-loader'), {
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <div className="text-center space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
        <p className="text-muted-foreground">Loading graph visualization...</p>
      </div>
    </div>
  ),
  ssr: false
})

interface VisGraphProps {
  fullscreen?: boolean
  selectedNodeId?: string | null
  selectedNodeType?: 'agent' | 'task' | 'context' | 'file' | 'admin' | null
  selectedNodeData?: any
  isPanelOpen?: boolean
  onNodeSelect?: (nodeId: string, nodeType: 'agent' | 'task' | 'context' | 'file' | 'admin', nodeData: any) => void
  onClosePanel?: () => void
}

export function VisGraph({ 
  fullscreen = false, 
  onNodeSelect
}: Pick<VisGraphProps, 'fullscreen' | 'onNodeSelect'>) {
  return (
    <VisNetworkComponent 
      fullscreen={fullscreen} 
      onNodeSelect={onNodeSelect}
    />
  )
}