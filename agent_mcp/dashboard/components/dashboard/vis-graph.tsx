"use client"

import React, { useEffect, useRef, useCallback, useState } from 'react'
import { Network, DataSet } from 'vis-network/standalone'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Network as NetworkIcon, Workflow, Eye, RefreshCw, 
  AlertCircle, GitBranch, Activity
} from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useServerStore } from '@/lib/stores/server-store'
import { cn } from '@/lib/utils'

// Physics options from the original implementation
const physicsOptions = {
  physics: {
    enabled: true,
    barnesHut: {
      gravitationalConstant: -5000,
      centralGravity: 0.2,
      springLength: 150,
      springConstant: 0.08,
      damping: 0.12,
      avoidOverlap: 0.5
    },
    maxVelocity: 50,
    minVelocity: 0.1,
    solver: 'barnesHut',
    stabilization: {
      enabled: true,
      iterations: 1000,
      updateInterval: 25,
      fit: true
    },
    adaptiveTimestep: true
  },
  layout: {
    hierarchical: { enabled: false }
  },
  nodes: {
    shape: 'box',
    borderWidth: 2,
    shadow: true,
    font: {
      size: 14,
      face: 'Segoe UI, sans-serif',
      color: 'rgba(241, 245, 249, 1)', // slate-100
      strokeWidth: 3,
      strokeColor: 'rgba(15, 23, 42, 0.8)' // slate-900 outline for better readability
    },
    scaling: {
      label: {
        enabled: true,
        min: 8,
        max: 20
      }
    }
  },
  edges: {
    width: 2,
    shadow: true,
    smooth: {
      enabled: true,
      type: 'continuous',
      forceDirection: 'none',
      roundness: 0.5
    },
    font: {
      size: 12,
      align: 'middle',
      background: 'rgba(15, 23, 42, 0.8)', // slate-900 with opacity
      color: 'rgba(148, 163, 184, 1)' // slate-400
    },
    arrows: {
      to: { enabled: true, scaleFactor: 0.8 }
    },
    color: {
      color: 'rgba(45, 212, 191, 0.5)', // teal-400 with lower opacity
      highlight: 'rgba(94, 234, 212, 0.9)', // teal-300 with high opacity
      hover: 'rgba(34, 211, 238, 0.8)' // cyan-400 with opacity
    }
  },
  groups: {
    agent: {
      shape: 'ellipse',
      borderWidth: 3,
      color: { 
        background: 'rgba(94, 234, 212, 0.9)', // teal-300 with opacity
        border: 'rgba(45, 212, 191, 1)', // teal-400
        highlight: {
          background: 'rgba(94, 234, 212, 1)',
          border: 'rgba(20, 184, 166, 1)' // teal-500
        }
      }
    },
    task: {
      shape: 'box',
      borderWidth: 2,
      color: { 
        background: 'rgba(34, 211, 238, 0.9)', // cyan-400 with opacity
        border: 'rgba(6, 182, 212, 1)', // cyan-500
        highlight: {
          background: 'rgba(34, 211, 238, 1)',
          border: 'rgba(8, 145, 178, 1)' // cyan-600
        }
      }
    },
    context: {
      shape: 'diamond',
      borderWidth: 2,
      color: { 
        background: 'rgba(147, 51, 234, 0.8)', // purple-600 with opacity
        border: 'rgba(124, 58, 237, 1)', // violet-600
        highlight: {
          background: 'rgba(147, 51, 234, 1)',
          border: 'rgba(109, 40, 217, 1)' // violet-700
        }
      }
    },
    file: {
      shape: 'triangle',
      borderWidth: 2,
      color: { 
        background: 'rgba(45, 212, 191, 0.8)', // teal-400 with opacity
        border: 'rgba(20, 184, 166, 1)', // teal-500
        highlight: {
          background: 'rgba(45, 212, 191, 1)',
          border: 'rgba(13, 148, 136, 1)' // teal-600
        }
      }
    },
    admin: {
      shape: 'star',
      borderWidth: 3,
      color: { 
        background: 'rgba(168, 85, 247, 0.9)', // purple-500 with opacity
        border: 'rgba(147, 51, 234, 1)', // purple-600
        highlight: {
          background: 'rgba(168, 85, 247, 1)',
          border: 'rgba(126, 34, 206, 1)' // purple-700
        }
      }
    }
  }
}

const hierarchicalOptions = {
  physics: { enabled: false },
  layout: {
    hierarchical: {
      enabled: true,
      levelSeparation: 250,
      nodeSpacing: 200,
      treeSpacing: 300,
      direction: 'UD', // Up-Down for vertical layout
      sortMethod: 'directed',
      shakeTowards: 'roots'
    }
  },
  nodes: {
    shape: 'box',
    borderWidth: 2,
    shadow: true,
    font: {
      size: 14,
      face: 'Segoe UI, sans-serif',
      color: 'rgba(241, 245, 249, 1)', // slate-100
      strokeWidth: 3,
      strokeColor: 'rgba(15, 23, 42, 0.8)' // slate-900 outline for better readability
    }
  },
  edges: {
    width: 2,
    shadow: true,
    smooth: {
      enabled: true,
      type: 'cubicBezier',
      forceDirection: 'vertical',
      roundness: 0.5
    },
    font: {
      size: 12,
      align: 'middle',
      background: 'rgba(15, 23, 42, 0.8)', // slate-900 with opacity
      color: 'rgba(148, 163, 184, 1)' // slate-400
    },
    arrows: {
      to: { enabled: true, scaleFactor: 0.8 }
    },
    color: {
      color: 'rgba(45, 212, 191, 0.5)', // teal-400 with lower opacity
      highlight: 'rgba(94, 234, 212, 0.9)', // teal-300 with high opacity
      hover: 'rgba(34, 211, 238, 0.8)' // cyan-400 with opacity
    }
  },
  groups: {
    agent: {
      shape: 'ellipse',
      borderWidth: 3,
      color: { 
        background: 'rgba(94, 234, 212, 0.9)', // teal-300 with opacity
        border: 'rgba(45, 212, 191, 1)', // teal-400
        highlight: {
          background: 'rgba(94, 234, 212, 1)',
          border: 'rgba(20, 184, 166, 1)' // teal-500
        }
      }
    },
    task: {
      shape: 'box',
      borderWidth: 2,
      color: { 
        background: 'rgba(34, 211, 238, 0.9)', // cyan-400 with opacity
        border: 'rgba(6, 182, 212, 1)', // cyan-500
        highlight: {
          background: 'rgba(34, 211, 238, 1)',
          border: 'rgba(8, 145, 178, 1)' // cyan-600
        }
      }
    },
    context: {
      shape: 'diamond',
      borderWidth: 2,
      color: { 
        background: 'rgba(147, 51, 234, 0.8)', // purple-600 with opacity
        border: 'rgba(124, 58, 237, 1)', // violet-600
        highlight: {
          background: 'rgba(147, 51, 234, 1)',
          border: 'rgba(109, 40, 217, 1)' // violet-700
        }
      }
    },
    file: {
      shape: 'triangle',
      borderWidth: 2,
      color: { 
        background: 'rgba(45, 212, 191, 0.8)', // teal-400 with opacity
        border: 'rgba(20, 184, 166, 1)', // teal-500
        highlight: {
          background: 'rgba(45, 212, 191, 1)',
          border: 'rgba(13, 148, 136, 1)' // teal-600
        }
      }
    },
    admin: {
      shape: 'star',
      borderWidth: 3,
      color: { 
        background: 'rgba(168, 85, 247, 0.9)', // purple-500 with opacity
        border: 'rgba(147, 51, 234, 1)', // purple-600
        highlight: {
          background: 'rgba(168, 85, 247, 1)',
          border: 'rgba(126, 34, 206, 1)' // purple-700
        }
      }
    }
  }
}

// Helper function to get node styling based on status
const getNodeStyling = (node: any) => {
  const baseSize = 15
  let size = baseSize
  let color = undefined
  let shape = 'box'

  if (node.group === 'agent') {
    size = baseSize + 10
    shape = 'ellipse'
    if (node.status === 'terminated') {
      color = { background: '#F44336', border: '#D32F2F' }
    } else if (node.color) {
      color = { background: node.color, border: node.color }
    } else {
      color = { background: '#4CAF50', border: '#2E7D32' }
    }
  } else if (node.group === 'task') {
    size = baseSize + 5
    shape = 'square'
    if (node.status === 'completed') {
      color = { background: '#9E9E9E', border: '#757575' }
    } else if (node.status === 'cancelled' || node.status === 'failed') {
      color = { background: '#FF9800', border: '#F57C00' }
    } else if (node.status === 'in_progress') {
      color = { background: '#2196F3', border: '#1976D2' }
    } else {
      color = { background: '#FFC107', border: '#FFA000' }
    }
  } else if (node.group === 'context') {
    size = baseSize
    shape = 'diamond'
    color = { background: '#9C27B0', border: '#7B1FA2' }
  } else if (node.group === 'file') {
    size = baseSize
    shape = 'triangle'
    color = { background: '#795548', border: '#5D4037' }
  } else if (node.group === 'admin') {
    size = baseSize + 10
    shape = 'star'
    color = { background: '#607D8B', border: '#455A64' }
  }

  return { size, color, shape }
}

interface VisGraphProps {
  fullscreen?: boolean
}

export function VisGraph({ fullscreen = false }: VisGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const nodesDataSetRef = useRef<DataSet<any>>(new DataSet())
  const edgesDataSetRef = useRef<DataSet<any>>(new DataSet())
  
  const { activeServerId, servers } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [layoutMode, setLayoutMode] = useState<'physics' | 'hierarchical'>('physics')
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [selectedNode, setSelectedNode] = useState<any>(null)
  const [nodeCount, setNodeCount] = useState(0)
  const [edgeCount, setEdgeCount] = useState(0)

  // Convert API data to vis.js format
  const convertToVisData = useCallback((graphData: any) => {
    if (!graphData || !graphData.nodes || !graphData.edges) {
      console.warn('Invalid graph data structure:', graphData)
      return
    }

    console.log(`[Graph] Converting ${graphData.nodes.length} nodes and ${graphData.edges.length} edges`)

    // Convert nodes
    const visNodes = graphData.nodes.map((node: any) => {
      const styling = getNodeStyling(node)
      
      return {
        id: node.id,
        label: node.label || node.id,
        title: node.title || `${node.group}: ${node.label}`,
        group: node.group,
        ...styling,
        ...node // Include all original properties
      }
    })

    // Convert edges
    const visEdges = graphData.edges.map((edge: any, index: number) => {
      const edgeStyle: any = {
        from: edge.from,
        to: edge.to,
        id: edge.id || `edge-${index}`,
        arrows: edge.arrows || { to: { enabled: true, scaleFactor: 0.5 } }
      }

      // Apply edge styling based on type
      if (edge.title) {
        edgeStyle.title = edge.title
        
        if (edge.title.includes('Created by')) {
          edgeStyle.color = { color: '#555555', opacity: 0.3 }
          edgeStyle.width = 0.5
        } else if (edge.title.includes('Parent of')) {
          edgeStyle.color = { color: '#10b981' }
          edgeStyle.width = 2
        } else if (edge.title.includes('Depends on')) {
          edgeStyle.color = { color: '#f59e0b' }
          edgeStyle.width = 1.5
          edgeStyle.dashes = true
        } else if (edge.title.includes('Working on')) {
          edgeStyle.color = { color: '#3b82f6' }
          edgeStyle.width = 2
          edgeStyle.smooth = { enabled: true, type: 'continuous' }
        } else if (edge.title.includes('accessing')) {
          edgeStyle.color = { color: '#ef4444' }
          edgeStyle.width = 1.5
          edgeStyle.label = edge.title.split(' ')[1]
        }
      }

      // Apply any custom edge properties from the API
      if (edge.color) edgeStyle.color = edge.color
      if (edge.width) edgeStyle.width = edge.width

      return edgeStyle
    })

    // Update the DataSets
    console.log('[Graph] Updating node and edge datasets.')
    nodesDataSetRef.current.clear()
    nodesDataSetRef.current.add(visNodes)
    edgesDataSetRef.current.clear()
    edgesDataSetRef.current.add(visEdges)
    
    setNodeCount(visNodes.length)
    setEdgeCount(visEdges.length)
  }, [])

  // Fetch graph data
  const fetchGraphData = useCallback(async () => {
    if (!activeServerId || !activeServer || activeServer.status !== 'connected') {
      setError('No active server connection')
      setLoading(false)
      return
    }

    console.log('[Graph] Fetching graph data...')
    try {
      setLoading(true)
      setError(null)
      
      const graphData = await apiClient.getGraphData()
      
      if (!graphData) {
        throw new Error('No data received from server')
      }
      
      console.log('[Graph] Data fetched successfully.')
      convertToVisData(graphData)

      if (networkRef.current && layoutMode === 'physics') {
        console.log('[Graph] Restarting physics simulation.')
        networkRef.current.startSimulation()
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch graph data'
      setError(errorMessage)
      console.error('Error fetching graph data:', err)
    } finally {
      setLoading(false)
    }
  }, [activeServerId, activeServer, convertToVisData, layoutMode])

  // Initialize vis.js network
  useEffect(() => {
    if (!containerRef.current) return

    const options = layoutMode === 'physics' ? physicsOptions : hierarchicalOptions

    const data = {
      nodes: nodesDataSetRef.current,
      edges: edgesDataSetRef.current
    }

    // Create network
    const network = new Network(containerRef.current, data, options)
    networkRef.current = network
    
    // Force physics to start
    if (layoutMode === 'physics') {
      network.startSimulation()
    }

    // Event handlers
    network.on('selectNode', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0]
        const node = nodesDataSetRef.current.get(nodeId)
        setSelectedNode(node)
      }
    })

    network.on('deselectNode', () => {
      setSelectedNode(null)
    })

    // Cleanup
    return () => {
      network.destroy()
      networkRef.current = null
    }
  }, [layoutMode])

  // Fetch data on mount and handle auto-refresh
  useEffect(() => {
    fetchGraphData()

    if (autoRefresh) {
      const interval = setInterval(fetchGraphData, 10000) // 10 seconds
      return () => clearInterval(interval)
    }
  }, [fetchGraphData, autoRefresh])

  

  // Handle layout mode change
  const handleLayoutChange = useCallback((mode: 'physics' | 'hierarchical') => {
    setLayoutMode(mode)
    if (networkRef.current) {
      const options = mode === 'physics' ? physicsOptions : hierarchicalOptions
      networkRef.current.setOptions(options)
      if (mode === 'physics') {
        // Force physics simulation to restart
        networkRef.current.startSimulation()
      }
      // Fit view after layout change
      setTimeout(() => {
        networkRef.current?.fit({ animation: true })
      }, 100)
    }
  }, [])

  if (!activeServerId || !activeServer || activeServer.status !== 'connected') {
    return (
      <Card>
        <CardHeader>
          <CardTitle>System Graph</CardTitle>
          <CardDescription>Visual representation of agents, tasks, and their relationships</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[600px] text-muted-foreground">
            <div className="text-center space-y-4">
              <NetworkIcon className="h-16 w-16 mx-auto opacity-50" />
              <div>
                <p className="text-lg font-medium">No active server connection</p>
                <p className="text-sm mt-2">Please select a server from the dropdown in the header to view the system graph</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>System Graph</CardTitle>
            <CardDescription>Visual representation of agents, tasks, and their relationships</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <div className="text-xs text-muted-foreground">
              {nodeCount} nodes, {edgeCount} edges
            </div>
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                variant={layoutMode === 'physics' ? 'default' : 'outline'}
                onClick={() => handleLayoutChange('physics')}
              >
                <Activity className="h-4 w-4 mr-1" />
                Physics
              </Button>
              <Button
                size="sm"
                variant={layoutMode === 'hierarchical' ? 'default' : 'outline'}
                onClick={() => handleLayoutChange('hierarchical')}
              >
                <GitBranch className="h-4 w-4 mr-1" />
                Hierarchy
              </Button>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={cn(autoRefresh && "bg-primary/10")}
            >
              <RefreshCw className={cn("h-4 w-4", autoRefresh && "animate-spin")} />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchGraphData}
              disabled={loading}
            >
              {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Refresh'}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <Tabs defaultValue="graph" className="h-full">
          <TabsList className="w-full rounded-none border-b">
            <TabsTrigger value="graph" className="flex-1">
              <Workflow className="h-4 w-4 mr-2" />
              Graph View
            </TabsTrigger>
            <TabsTrigger value="details" className="flex-1">
              <Eye className="h-4 w-4 mr-2" />
              Node Details
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="graph" className={cn("m-0", fullscreen ? "h-full" : "h-[800px]")}>
            {loading && nodeCount === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center space-y-4">
                  <RefreshCw className="h-12 w-12 mx-auto animate-spin text-primary" />
                  <p className="text-muted-foreground">Loading graph data...</p>
                </div>
              </div>
            ) : error && nodeCount === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center space-y-4">
                  <AlertCircle className="h-12 w-12 mx-auto text-destructive" />
                  <p className="text-muted-foreground">{error}</p>
                  <Button onClick={fetchGraphData} variant="outline">
                    Retry
                  </Button>
                </div>
              </div>
            ) : (
              <div ref={containerRef} className="w-full h-full bg-slate-950 rounded-lg" />
            )}
          </TabsContent>
          
          <TabsContent value="details" className="p-6">
            {selectedNode ? (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">
                  {selectedNode.label}
                </h3>
                <div className="grid gap-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Type:</span>
                    <span className="font-medium">{selectedNode.group}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">ID:</span>
                    <span className="font-mono text-xs">{selectedNode.id}</span>
                  </div>
                  {selectedNode.status && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Status:</span>
                      <Badge variant="outline">{selectedNode.status}</Badge>
                    </div>
                  )}
                  {selectedNode.title && (
                    <div className="mt-4">
                      <span className="text-muted-foreground">Details:</span>
                      <pre className="mt-1 text-xs whitespace-pre-wrap">{selectedNode.title}</pre>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <div className="text-center">
                  <Eye className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>Select a node to view details</p>
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}