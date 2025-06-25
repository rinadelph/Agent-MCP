"use client"

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  ConnectionMode,
  Panel,
  ReactFlowProvider,
  BackgroundVariant,
  MarkerType,
  NodeTypes,
  EdgeTypes,
  Handle,
  Position,
  NodeProps,
  EdgeProps,
  getBezierPath,
  BaseEdge,
  EdgeLabelRenderer,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  FileText, Database, 
  GitBranch, Network, Workflow,
  Eye, EyeOff, RefreshCw, AlertCircle
} from 'lucide-react'
import { useTheme } from '@/lib/store'
import { apiClient } from '@/lib/api'
import { useServerStore } from '@/lib/stores/server-store'
import { cn } from '@/lib/utils'
import type { GraphNode, GraphEdge } from '@/lib/api'

// Custom Node Types
const AgentNode = ({ data, selected }: NodeProps) => {
  console.log('Rendering AgentNode:', data.label, data)
  const statusColors: {[key: string]: string} = {
    active: 'bg-green-500',
    created: 'bg-blue-500',
    terminated: 'bg-gray-500'
  }

  return (
    <div 
      className={cn(
        "px-4 py-3 rounded-lg border-2 transition-all",
        selected ? "border-primary shadow-lg" : "border-border"
      )}
      style={{
        background: statusColors[data.status] === 'bg-green-500' ? '#4CAF50' : 
                   statusColors[data.status] === 'bg-blue-500' ? '#2196F3' : '#9E9E9E',
        color: 'white',
        minWidth: '150px'
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#555' }} />
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 rounded-full bg-white/30" />
        <div>
          <div className="font-semibold text-sm">{data.label}</div>
          <div className="text-xs opacity-80">{data.status}</div>
          {data.current_task && (
            <div className="text-xs opacity-70 mt-1">→ {data.current_task}</div>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: '#555' }} />
    </div>
  )
}

const TaskNode = ({ data, selected }: NodeProps) => {
  console.log('Rendering TaskNode:', data.label, data)

  const getTaskColor = (status: string) => {
    switch(status) {
      case 'completed': return '#9E9E9E'
      case 'cancelled': 
      case 'failed': return '#FF9800'
      case 'in_progress': return '#2196F3'
      case 'pending': 
      default: return '#FFC107'
    }
  }

  return (
    <div 
      className={cn(
        "px-3 py-2 rounded-md border transition-all",
        selected ? "border-primary shadow-lg" : "border-gray-600"
      )}
      style={{
        background: getTaskColor(data.status),
        color: data.status === 'pending' ? '#333' : 'white',
        minWidth: '200px',
        borderWidth: '2px'
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#555' }} />
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="font-medium text-sm truncate">{data.label}</div>
          <div className="text-xs opacity-80 mt-1">{data.status}</div>
        </div>
        {data.priority && (
          <div className={cn(
            "text-xs px-2 py-0.5 rounded",
            data.priority === 'high' ? 'bg-red-900/50' : 
            data.priority === 'medium' ? 'bg-yellow-900/50' : 'bg-blue-900/50'
          )}>
            {data.priority}
          </div>
        )}
      </div>
      {data.assigned_to && (
        <div className="text-xs opacity-70 mt-1">→ {data.assigned_to}</div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: '#555' }} />
    </div>
  )
}

const ContextNode = ({ data, selected }: NodeProps) => {
  return (
    <div className={cn(
      "px-3 py-2 rounded border bg-card/50 backdrop-blur transition-all",
      selected ? "border-primary shadow-lg" : "border-border/50"
    )}>
      <Handle type="target" position={Position.Left} className="w-2 h-2" />
      <div className="flex items-center gap-2">
        <Database className="h-3 w-3 text-muted-foreground" />
        <div className="text-xs font-medium">{data.label}</div>
      </div>
      <Handle type="source" position={Position.Right} className="w-2 h-2" />
    </div>
  )
}

const FileNode = ({ data, selected }: NodeProps) => {
  const statusColors: {[key: string]: string} = {
    reading: 'text-blue-600',
    editing: 'text-orange-600',
    locked: 'text-red-600'
  }

  return (
    <div className={cn(
      "px-3 py-2 rounded border bg-card/50 backdrop-blur transition-all",
      selected ? "border-primary shadow-lg" : "border-border/50"
    )}>
      <Handle type="target" position={Position.Top} className="w-2 h-2" />
      <div className="flex items-center gap-2">
        <FileText className={cn("h-3 w-3", statusColors[data.status] || 'text-muted-foreground')} />
        <div className="text-xs">
          <div className="font-medium truncate max-w-[150px]">{data.label}</div>
          {data.status && (
            <div className={cn("text-xs", statusColors[data.status])}>{data.status}</div>
          )}
        </div>
      </div>
    </div>
  )
}

// Custom Edge Types
const CustomEdge = ({ 
  id, 
  sourceX, 
  sourceY, 
  targetX, 
  targetY, 
  sourcePosition, 
  targetPosition, 
  data,
  style,
  markerEnd
}: EdgeProps) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  })

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={style} markerEnd={markerEnd} />
      {data?.label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              fontSize: 10,
              pointerEvents: 'all',
            }}
            className="px-2 py-1 rounded bg-background/80 backdrop-blur text-xs border border-border/50"
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}

// Define nodeTypes and edgeTypes outside the component to prevent recreation
const nodeTypes: NodeTypes = {
  agent: AgentNode,
  task: TaskNode,
  context: ContextNode,
  file: FileNode,
}

const edgeTypes: EdgeTypes = {
  custom: CustomEdge,
}

// Simple default node types for testing
const defaultNodeTypes: NodeTypes = {}

// Main System Graph Component
export function SystemGraph() {
  const { } = useTheme() // theme available if needed
  const { activeServerId, servers } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [layoutType, setLayoutType] = useState<'physics' | 'hierarchical'>('physics')
  const [showLabels, setShowLabels] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [debugMode, setDebugMode] = useState(false)

  // Convert API data to React Flow format
  const convertToFlowData = useCallback((graphData: { nodes: GraphNode[], edges: GraphEdge[] }, isDebugMode: boolean) => {
    try {
      if (!graphData || !graphData.nodes || !graphData.edges) {
        console.warn('Invalid graph data structure:', graphData)
        return
      }

      console.log(`Converting ${graphData.nodes.length} nodes and ${graphData.edges.length} edges`)
      console.log('Sample node:', graphData.nodes[0])
      console.log('Sample edge:', graphData.edges[0])

      // Convert nodes
      const flowNodes: Node[] = graphData.nodes.map((node: GraphNode, index: number) => {
        let type = 'default'
        let position = { x: 0, y: 0 }

        // Determine node type and initial position based on group
        if (!isDebugMode) {
          if (node.group === 'agent') {
            type = 'agent'
            position = { x: 100 + (index % 3) * 300, y: 100 }
          } else if (node.group === 'task') {
            type = 'task'
            position = { x: 100 + (index % 4) * 250, y: 300 + Math.floor(index / 4) * 150 }
          } else if (node.group === 'context') {
            type = 'context'
            position = { x: 800, y: 100 + index * 80 }
          } else if (node.group === 'file') {
            type = 'file'
            position = { x: 600, y: 500 + index * 60 }
          } else if (node.group === 'admin') {
            type = 'agent' // Use agent type for admin
            position = { x: 400, y: 50 }
          }
        } else {
          // Simple layout for debug mode
          position = { x: 200 + (index % 5) * 150, y: 100 + Math.floor(index / 5) * 100 }
        }

        const flowNode = {
          id: node.id,
          type,
          position,
          data: {
            ...node,
            label: node.label || node.id,
          }
        }
        
        console.log(`Created node: ${node.id}, type: ${type}, group: ${node.group}, position:`, position)
        return flowNode
      })

      // Create a set of valid node IDs for edge validation
      const validNodeIds = new Set(flowNodes.map(n => n.id))
      console.log('Valid node IDs:', Array.from(validNodeIds))

      // Convert edges and validate node references
      const flowEdges: Edge[] = []
      graphData.edges.forEach((edge: GraphEdge, index: number) => {
        // Validate edge has required fields
        if (!edge.from || !edge.to) {
          console.warn(`Edge ${index} missing from/to:`, edge)
          return
        }

        // Check if both nodes exist
        if (!validNodeIds.has(edge.from) || !validNodeIds.has(edge.to)) {
          console.warn(`Edge references non-existent nodes: ${edge.from} -> ${edge.to}`)
          return
        }

        let style = {}
        let markerEnd = undefined
        let animated = false
        let label = undefined

        // Style edges based on their type
        if (edge.title?.includes('Created by')) {
          style = { stroke: '#888', strokeWidth: 1, opacity: 0.3 }
        } else if (edge.title?.includes('Parent of')) {
          style = { stroke: '#10b981', strokeWidth: 2 }
          markerEnd = { type: MarkerType.ArrowClosed, color: '#10b981' }
        } else if (edge.title?.includes('Depends on')) {
          style = { stroke: '#f59e0b', strokeWidth: 1.5, strokeDasharray: '5,5' }
          markerEnd = { type: MarkerType.Arrow, color: '#f59e0b' }
        } else if (edge.title?.includes('Working on')) {
          style = { stroke: '#3b82f6', strokeWidth: 2 }
          animated = true
          markerEnd = { type: MarkerType.ArrowClosed, color: '#3b82f6' }
        } else if (edge.title?.includes('accessing')) {
          style = { stroke: '#ef4444', strokeWidth: 1.5 }
          label = edge.title.split(' ')[1] // Show file operation
        }

        flowEdges.push({
          id: `edge-${index}`,
          source: edge.from,
          target: edge.to,
          type: 'custom',
          animated,
          style,
          markerEnd,
          data: { label }
        })
      })

      console.log(`Converted to ${flowNodes.length} nodes and ${flowEdges.length} valid edges`)
      
      // Test with simple nodes first
      const testNodes: Node[] = [
        {
          id: 'test-1',
          type: 'default',
          position: { x: 250, y: 100 },
          data: { label: 'Test Node 1' }
        },
        {
          id: 'test-2',
          type: 'default',
          position: { x: 100, y: 200 },
          data: { label: 'Test Node 2' }
        },
        {
          id: 'test-3',
          type: 'default',
          position: { x: 400, y: 200 },
          data: { label: 'Test Node 3' }
        }
      ]
      
      const testEdges: Edge[] = [
        {
          id: 'e1-2',
          source: 'test-1',
          target: 'test-2',
          type: 'default'
        },
        {
          id: 'e1-3',
          source: 'test-1',
          target: 'test-3',
          type: 'default'
        }
      ]
      
      // Test with simple nodes in debug mode
      if (isDebugMode) {
        console.log('Debug mode: Using test nodes')
        setNodes(testNodes)
        setEdges(testEdges)
      } else {
        // Use real data
        setNodes(flowNodes)
        setEdges(flowEdges)
      }
    } catch (error) {
      console.error('Error converting graph data:', error)
      setError('Failed to process graph data')
    }
  }, [setNodes, setEdges, setError])

  // Fetch graph data
  const fetchGraphData = useCallback(async () => {
    if (!activeServerId || !activeServer || activeServer.status !== 'connected') {
      setNodes([])
      setEdges([])
      setError('No active server connection')
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)
      
      console.log('Fetching graph data from:', apiClient.getServerUrl())
      const graphData = await apiClient.getGraphData()
      console.log('Raw graph data received:', graphData)
      
      if (!graphData) {
        throw new Error('No data received from server')
      }
      
      convertToFlowData(graphData, debugMode)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch graph data'
      setError(errorMessage)
      console.error('Error fetching graph data:', err)
      
      // Log more details for debugging
      if (err instanceof Error && err.message.includes('404')) {
        console.error('API endpoint not found. Check if the backend is running and the routes are correct.')
      }
    } finally {
      setLoading(false)
    }
  }, [activeServerId, activeServer, convertToFlowData, setNodes, setEdges, debugMode])

  // Initial load and auto-refresh
  useEffect(() => {
    console.log('SystemGraph mounted, fetching initial data...')
    fetchGraphData()

    if (autoRefresh) {
      const interval = setInterval(fetchGraphData, 5000) // Refresh every 5 seconds
      return () => clearInterval(interval)
    }
  }, [fetchGraphData, autoRefresh])
  
  // Debug: Check if nodes have valid positions
  useEffect(() => {
    if (nodes.length > 0) {
      const nodesWithInvalidPos = nodes.filter(n => !n.position || n.position.x === undefined || n.position.y === undefined)
      if (nodesWithInvalidPos.length > 0) {
        console.error('Nodes with invalid positions:', nodesWithInvalidPos)
      }
    }
  }, [nodes])

  // Debug logging for React Flow
  useEffect(() => {
    console.log('React Flow State:', {
      nodesCount: nodes.length,
      edgesCount: edges.length,
      nodes: nodes.slice(0, 5), // Log first 5 nodes
      edges: edges.slice(0, 5), // Log first 5 edges
      loading,
      error
    })
  }, [nodes, edges, loading, error])

  // Handle node selection
  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id)
  }, [])

  // Layout algorithms
  const applyHierarchicalLayout = useCallback(() => {
    const layoutNodes = [...nodes]
    const nodeMap = new Map(layoutNodes.map(n => [n.id, n]))
    
    // Find root nodes (no incoming edges)
    const incomingEdges = new Map<string, number>()
    edges.forEach(edge => {
      incomingEdges.set(edge.target, (incomingEdges.get(edge.target) || 0) + 1)
    })
    
    const roots = layoutNodes.filter(n => !incomingEdges.has(n.id))
    const visited = new Set<string>()
    const levels = new Map<string, number>()
    
    // BFS to assign levels
    const queue = roots.map(r => ({ node: r, level: 0 }))
    while (queue.length > 0) {
      const { node, level } = queue.shift()!
      if (visited.has(node.id)) continue
      
      visited.add(node.id)
      levels.set(node.id, level)
      
      // Find children
      const children = edges
        .filter(e => e.source === node.id)
        .map(e => nodeMap.get(e.target))
        .filter(Boolean) as Node[]
      
      children.forEach(child => {
        queue.push({ node: child, level: level + 1 })
      })
    }
    
    // Position nodes by level
    const levelNodes = new Map<number, Node[]>()
    layoutNodes.forEach(node => {
      const level = levels.get(node.id) || 0
      if (!levelNodes.has(level)) levelNodes.set(level, [])
      levelNodes.get(level)!.push(node)
    })
    
    levelNodes.forEach((nodes, level) => {
      const spacing = 250
      const y = 100 + level * 200
      nodes.forEach((node, index) => {
        node.position = {
          x: 100 + index * spacing,
          y
        }
      })
    })
    
    setNodes(layoutNodes)
  }, [nodes, edges, setNodes])

  const selectedNode = useMemo(() => {
    return nodes.find(n => n.id === selectedNodeId)
  }, [nodes, selectedNodeId])

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
              <Network className="h-16 w-16 mx-auto opacity-50" />
              <div>
                <p className="text-lg font-medium">No active server connection</p>
                <p className="text-sm mt-2">Please select a server from the dropdown in the header to view the system graph</p>
              </div>
              {servers.length > 0 && (
                <div className="mt-6">
                  <p className="text-xs text-muted-foreground mb-2">Available servers:</p>
                  <div className="space-y-1">
                    {servers.map(server => (
                      <div key={server.id} className="text-xs">
                        {server.name} ({server.host}:{server.port})
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Show loading state
  if (loading && nodes.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>System Graph</CardTitle>
          <CardDescription>Visual representation of agents, tasks, and their relationships</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[600px]">
            <div className="text-center space-y-4">
              <RefreshCw className="h-12 w-12 mx-auto animate-spin text-primary" />
              <p className="text-muted-foreground">Loading graph data...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Show error state
  if (error && nodes.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>System Graph</CardTitle>
          <CardDescription>Visual representation of agents, tasks, and their relationships</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[600px]">
            <div className="text-center space-y-4">
              <AlertCircle className="h-12 w-12 mx-auto text-destructive" />
              <p className="text-muted-foreground">{error}</p>
              <Button onClick={() => fetchGraphData()} variant="outline">
                Retry
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="h-[700px] flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>System Graph</CardTitle>
            <CardDescription>Visual representation of agents, tasks, and their relationships</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <div className="text-xs text-muted-foreground">
              {nodes.length} nodes, {edges.length} edges
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowLabels(!showLabels)}
            >
              {showLabels ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
            </Button>
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
      <CardContent className="p-0 flex-grow">
        <Tabs defaultValue="graph" className="h-full flex flex-col">
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
          
          <TabsContent value="graph" className="flex-grow m-0 relative overflow-hidden">
            <ReactFlowProvider>
              <div className="absolute inset-0" style={{ width: '100%', height: '100%' }}>
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onNodeClick={onNodeClick}
                  nodeTypes={debugMode ? defaultNodeTypes : nodeTypes}
                  edgeTypes={debugMode ? {} : edgeTypes}
                  connectionMode={ConnectionMode.Loose}
                  fitView={true}
                  minZoom={0.1}
                  maxZoom={2}
                  defaultViewport={{ x: 0, y: 0, zoom: 0.5 }}
                  className="bg-background"
                  onInit={(instance) => {
                    console.log('React Flow initialized:', instance)
                    console.log('Nodes in view:', instance.getNodes())
                    console.log('Edges in view:', instance.getEdges())
                    console.log('Viewport:', instance.getViewport())
                    console.log('Node types registered:', Object.keys(nodeTypes))
                    // Force a fit view after initialization
                    setTimeout(() => {
                      instance.fitView({ padding: 0.2, maxZoom: 1 })
                      console.log('After fit view - Viewport:', instance.getViewport())
                      // console.log('Bounds:', instance.getNodesBounds(instance.getNodes()))
                    }, 500)
                  }}
                  onError={(id, message) => {
                    console.error('React Flow error:', id, message)
                  }}
                >
                <Background 
                  variant={BackgroundVariant.Dots}
                  gap={12}
                  size={1}
                  className="bg-muted/20"
                />
                <Controls className="bg-background border border-border" />
                <Panel position="top-left" className="bg-background/80 backdrop-blur p-2 rounded border border-border">
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant={layoutType === 'physics' ? 'default' : 'outline'}
                      onClick={() => setLayoutType('physics')}
                    >
                      <Network className="h-4 w-4 mr-1" />
                      Physics
                    </Button>
                    <Button
                      size="sm"
                      variant={layoutType === 'hierarchical' ? 'default' : 'outline'}
                      onClick={() => {
                        setLayoutType('hierarchical')
                        applyHierarchicalLayout()
                      }}
                    >
                      <GitBranch className="h-4 w-4 mr-1" />
                      Hierarchy
                    </Button>
                    <Button
                      size="sm"
                      variant={debugMode ? 'default' : 'outline'}
                      onClick={() => setDebugMode(!debugMode)}
                    >
                      Debug
                    </Button>
                  </div>
                </Panel>
                <Panel position="bottom-left" className="bg-background/80 backdrop-blur p-3 rounded border border-border">
                  <div className="text-xs space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-green-500" />
                      <span>Active/Completed</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-blue-500" />
                      <span>In Progress</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-yellow-500" />
                      <span>Pending</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500" />
                      <span>Failed</span>
                    </div>
                  </div>
                </Panel>
                </ReactFlow>
              </div>
            </ReactFlowProvider>
          </TabsContent>
          
          <TabsContent value="details" className="p-6">
            {selectedNode ? (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">
                  {selectedNode.data.label}
                </h3>
                <div className="grid gap-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Type:</span>
                    <span className="font-medium">{selectedNode.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">ID:</span>
                    <span className="font-mono text-xs">{selectedNode.id}</span>
                  </div>
                  {selectedNode.data.status && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Status:</span>
                      <Badge variant="outline">{selectedNode.data.status}</Badge>
                    </div>
                  )}
                  {selectedNode.data.priority && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Priority:</span>
                      <Badge variant="secondary">{selectedNode.data.priority}</Badge>
                    </div>
                  )}
                  {selectedNode.data.assignedTo && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Assigned to:</span>
                      <span className="font-medium">{selectedNode.data.assignedTo}</span>
                    </div>
                  )}
                  {selectedNode.data.description && (
                    <div className="mt-4">
                      <span className="text-muted-foreground">Description:</span>
                      <p className="mt-1 text-sm">{selectedNode.data.description}</p>
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