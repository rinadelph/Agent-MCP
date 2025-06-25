"use client"

import React, { useEffect, useRef, useCallback, useState, Profiler } from 'react'
import { Network, DataSet } from 'vis-network/standalone'

interface VisNode {
  id: string;
  label?: string;
  group?: string;
  x?: number;
  y?: number;
  fixed?: boolean;
  physics?: boolean;
  color?: string | { background?: string; border?: string; highlight?: { background?: string; border?: string } };
  shape?: string;
  size?: number;
  [key: string]: unknown;
}

interface VisEdge {
  id?: string;
  from: string;
  to: string;
  arrows?: { to?: { enabled?: boolean; scaleFactor?: number } };
  color?: string | { color?: string; highlight?: string; hover?: string };
  width?: number;
  dashes?: boolean;
  [key: string]: unknown;
}
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  RefreshCw, GitBranch, Activity, Layers
} from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useServerStore } from '@/lib/stores/server-store'
import { cn } from '@/lib/utils'

// Physics options with better spacing and clustering
const physicsOptions = {
  physics: {
    enabled: true,
    barnesHut: {
      gravitationalConstant: -12000, // Strong repulsion for better separation
      centralGravity: 0.05, // Very low to prevent clustering at center
      springLength: 250, // Longer springs for more space
      springConstant: 0.02, // Softer springs
      damping: 0.2,
      avoidOverlap: 1 // Maximum overlap avoidance
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
    adaptiveTimestep: true,
    timestep: 0.5
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
      color: '#ffffff'
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
      background: 'rgba(40, 44, 52, 0.8)'
    },
    arrows: {
      to: { enabled: true, scaleFactor: 0.8 }
    }
  },
  groups: {
    agent: {
      shape: 'ellipse',
      borderWidth: 3,
      color: { background: '#4CAF50', border: '#2E7D32' }
    },
    task: {
      shape: 'box',
      borderWidth: 2,
      color: { background: '#FFC107', border: '#FFA000' }
    },
    context: {
      shape: 'diamond',
      borderWidth: 3,
      color: { background: '#9C27B0', border: '#7B1FA2' },
      shapeProperties: {
        borderDashes: false
      },
      size: 30
    },
    file: {
      shape: 'triangle',
      borderWidth: 2,
      color: { background: '#795548', border: '#5D4037' }
    },
    admin: {
      shape: 'star',
      borderWidth: 4,
      color: { background: '#e11d48', border: '#be123c' },
      font: { size: 16, color: '#ffffff', bold: true }
    }
  }
}

const hierarchicalOptions = {
  physics: { 
    enabled: true,
    hierarchicalRepulsion: {
      centralGravity: 0,
      springLength: 200,
      springConstant: 0.01,
      nodeDistance: 250,
      damping: 0.09
    },
    solver: 'hierarchicalRepulsion'
  },
  layout: {
    hierarchical: {
      enabled: true,
      levelSeparation: 300,
      nodeSpacing: 250,
      treeSpacing: 400,
      direction: 'UD', // Up-Down for vertical layout
      sortMethod: 'directed',
      shakeTowards: 'roots',
      parentCentralization: true,
      edgeMinimization: true,
      blockShifting: true
    }
  },
  nodes: physicsOptions.nodes,
  edges: {
    ...physicsOptions.edges,
    smooth: {
      enabled: true,
      type: 'cubicBezier',
      forceDirection: 'vertical',
      roundness: 0.5
    }
  },
  groups: physicsOptions.groups
}

// Get node styling based on type
const getNodeStyling = (node: any) => {
  const baseSize = 25
  let size = baseSize
  let color: any = {}
  let shape = 'box'

  if (node.group === 'agent') {
    size = baseSize + 10
    shape = 'ellipse'
    if (node.status === 'terminated') {
      color = { background: '#F44336', border: '#D32F2F' }
    } else if (node.color) {
      color = { background: node.color, border: '#2E7D32' }
    } else {
      color = { background: '#4CAF50', border: '#2E7D32' }
    }
  } else if (node.group === 'task') {
    size = baseSize + 5
    shape = 'box'
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
    size = baseSize + 20
    shape = 'star'
    color = { background: '#e11d48', border: '#be123c' }
  }

  return { size, color, shape }
}

interface VisGraphProps {
  fullscreen?: boolean
  selectedNodeId?: string | null
  selectedNodeType?: 'agent' | 'task' | 'context' | 'file' | 'admin' | null
  selectedNodeData?: any
  isPanelOpen?: boolean
  onNodeSelect?: (nodeId: string, nodeType: 'agent' | 'task' | 'context' | 'file' | 'admin', nodeData: any) => void
  onClosePanel?: () => void
}

// Performance profiling callback for vis graph
const onVisGraphRender = (id: string, phase: "mount" | "update" | "nested-update", actualDuration: number) => {
  if (actualDuration > 16.67) { // Log if render takes longer than 60fps (16.67ms)
    console.warn(`[VisGraph] Slow render detected: ${actualDuration.toFixed(2)}ms for ${phase}`)
  }
}

export function VisGraph({ 
  fullscreen = false, 
  onNodeSelect
}: Pick<VisGraphProps, 'fullscreen' | 'onNodeSelect'>) {
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const nodesDataSetRef = useRef<DataSet<VisNode>>(new DataSet())
  const edgesDataSetRef = useRef<DataSet<VisEdge>>(new DataSet())
  
  const { activeServerId, servers } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [layoutMode, setLayoutMode] = useState<'physics' | 'hierarchical'>('physics')
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [nodeCount, setNodeCount] = useState(0)
  const [edgeCount, setEdgeCount] = useState(0)
  const [isMounted, setIsMounted] = useState(false)
  
  // Track mounted state
  useEffect(() => {
    setIsMounted(true)
    return () => {
      setIsMounted(false)
    }
  }, [])

  // Convert API data to vis.js format with smart diffing
  const convertToVisData = useCallback((graphData: any) => {
    performance.mark('vis-data-conversion-start')
    
    if (!graphData || !graphData.nodes || !graphData.edges) {
      console.warn('Invalid graph data structure:', graphData)
      return
    }

    // Get current nodes and edges
    const currentNodeIds = new Set(nodesDataSetRef.current.getIds())
    const currentEdgeIds = new Set(edgesDataSetRef.current.getIds())

    // Filter out idle agents (agents with no edges connecting to them)
    const nodeIdsWithConnections = new Set<string>()
    graphData.edges.forEach((edge: { from: string; to: string }) => {
      nodeIdsWithConnections.add(edge.from)
      nodeIdsWithConnections.add(edge.to)
    })

    // Filter nodes - keep admin, non-agents, and agents with connections
    const filteredNodes = graphData.nodes.filter((node: { group?: string; id: string }) => {
      // In tree mode, only show tasks
      if (layoutMode === 'hierarchical') {
        return node.group === 'task' || node.group === 'file'
      }
      
      // In physics mode, show everything
      if (node.group === 'admin') return true // Always show admin
      if (node.group !== 'agent') return true // Show all non-agents
      return nodeIdsWithConnections.has(node.id) // Only show agents with connections
    })

    // Separate nodes by type for better organization
    const contextNodes = filteredNodes.filter((n: { group?: string }) => n.group === 'context')
    const taskNodes = filteredNodes.filter((n: { group?: string }) => n.group === 'task')
    
    // Convert nodes with organized positioning
    const visNodes = filteredNodes.map((node: { id: string; group?: string; label?: string; [key: string]: unknown }) => {
      const styling = getNodeStyling(node)
      
      // Fixed position for admin node at center
      if (node.group === 'admin') {
        return {
          ...node,
          label: node.label || node.id,
          fixed: { x: true, y: true },
          x: 0,
          y: 0,
          physics: false, // Disable physics for admin node
          ...styling,
          title: undefined // Explicitly remove any title that might come from node data
        }
      }
      
      // Position context nodes in a crown/circle around admin
      if (node.group === 'context') {
        const contextIndex = contextNodes.findIndex((n: any) => n.id === node.id)
        const angleStep = (2 * Math.PI) / contextNodes.length
        const angle = contextIndex * angleStep
        const radius = 400 // Fixed radius for the crown
        
        return {
          ...node,
          label: node.label || node.id,
          x: Math.cos(angle) * radius,
          y: Math.sin(angle) * radius,
          fixed: { x: true, y: true }, // Fix context nodes in crown position
          physics: false, // Disable physics for context nodes
          ...styling,
          title: undefined // Explicitly remove any title that might come from node data
        }
      }
      
      // Position task nodes in an outer ring
      if (node.group === 'task') {
        const taskIndex = taskNodes.findIndex((n: any) => n.id === node.id)
        const angleStep = (2 * Math.PI) / taskNodes.length
        const angle = taskIndex * angleStep + (Math.PI / taskNodes.length) // Offset to avoid alignment
        const radius = 600 + (taskIndex % 2) * 100 // Alternate between two radii
        
        return {
          ...node,
          label: node.label || node.id,
          x: Math.cos(angle) * radius,
          y: Math.sin(angle) * radius,
          ...styling,
          title: undefined // Explicitly remove any title that might come from node data
        }
      }
      
      // Let other nodes use physics
      return {
        ...node,
        label: node.label || node.id,
        ...styling
      }
    })

    // Convert edges - filter based on layout mode
    const visEdges = graphData.edges.filter((edge: any) => {
      // In tree mode, only show edges between visible nodes
      if (layoutMode === 'hierarchical') {
        const fromNode = filteredNodes.find((n: any) => n.id === edge.from)
        const toNode = filteredNodes.find((n: any) => n.id === edge.to)
        
        // Only keep edges where both nodes are visible
        return fromNode && toNode
      }
      return true
    }).map((edge: any, index: number) => {
      const edgeStyle: any = {
        from: edge.from,
        to: edge.to,
        id: edge.id || `edge-${index}`,
        arrows: edge.arrows || { to: { enabled: true, scaleFactor: 0.5 } }
      }

      // Apply edge styling based on type
      if (edge.title) {
        // Don't add title to prevent hover tooltips
        // edgeStyle.title = edge.title
        
        if (edge.title.includes('Created by')) {
          edgeStyle.color = { color: '#555555', opacity: 0.2 }
          edgeStyle.width = 0.5
          edgeStyle.dashes = [2, 4]
        } else if (edge.title.includes('Parent of')) {
          edgeStyle.color = { color: '#10b981' }
          edgeStyle.width = 3
          edgeStyle.smooth = { enabled: true, type: 'curvedCW', roundness: 0.2 }
        } else if (edge.title.includes('Depends on')) {
          edgeStyle.color = { color: '#f59e0b' }
          edgeStyle.width = 2
          edgeStyle.dashes = true
          edgeStyle.smooth = { enabled: true, type: 'curvedCCW', roundness: 0.2 }
        } else if (edge.title.includes('Working on')) {
          edgeStyle.color = { color: '#3b82f6' }
          edgeStyle.width = 3
          edgeStyle.smooth = { enabled: true, type: 'continuous' }
        }
      }
      
      // Special styling for edges to/from context nodes
      if (edge.from.includes('context') || edge.to.includes('context')) {
        edgeStyle.color = { color: '#9333ea', opacity: 0.3 }
        edgeStyle.width = 1
        edgeStyle.dashes = [3, 6]
        edgeStyle.smooth = { enabled: true, type: 'continuous', roundness: 0.8 }
        edgeStyle.arrows = { to: { enabled: true, scaleFactor: 0.3 } }
      }

      // Apply any custom edge properties from the API
      if (edge.color) edgeStyle.color = edge.color
      if (edge.width) edgeStyle.width = edge.width

      return edgeStyle
    })

    // Smart update - only update what's changed
    const newNodeIds = new Set(visNodes.map((n: any) => n.id))
    const newEdgeIds = new Set(visEdges.map((e: any) => e.id))

    // Find nodes to remove, update, and add
    const nodesToRemove = Array.from(currentNodeIds).filter(id => !newNodeIds.has(id))
    const nodesToUpdate: any[] = []
    const nodesToAdd: any[] = []

    visNodes.forEach((node: any) => {
      if (currentNodeIds.has(node.id)) {
        // Check if node has actually changed
        const currentNode = nodesDataSetRef.current.get(node.id)
        if (JSON.stringify(currentNode) !== JSON.stringify(node)) {
          nodesToUpdate.push(node)
        }
      } else {
        nodesToAdd.push(node)
      }
    })

    // Find edges to remove, update, and add
    const edgesToRemove = Array.from(currentEdgeIds).filter(id => !newEdgeIds.has(id))
    const edgesToUpdate: any[] = []
    const edgesToAdd: any[] = []

    visEdges.forEach((edge: any) => {
      if (currentEdgeIds.has(edge.id)) {
        // Check if edge has actually changed
        const currentEdge = edgesDataSetRef.current.get(edge.id)
        if (JSON.stringify(currentEdge) !== JSON.stringify(edge)) {
          edgesToUpdate.push(edge)
        }
      } else {
        edgesToAdd.push(edge)
      }
    })

    // Apply updates only if there are changes
    if (nodesToRemove.length > 0) {
      nodesDataSetRef.current.remove(nodesToRemove)
    }
    if (nodesToUpdate.length > 0) {
      nodesDataSetRef.current.update(nodesToUpdate)
    }
    if (nodesToAdd.length > 0) {
      nodesDataSetRef.current.add(nodesToAdd)
    }

    if (edgesToRemove.length > 0) {
      edgesDataSetRef.current.remove(edgesToRemove)
    }
    if (edgesToUpdate.length > 0) {
      edgesDataSetRef.current.update(edgesToUpdate)
    }
    if (edgesToAdd.length > 0) {
      edgesDataSetRef.current.add(edgesToAdd)
    }

    setNodeCount(visNodes.length)
    setEdgeCount(visEdges.length)

    // Only fit to view if it's the first load or significant changes
    if (currentNodeIds.size === 0 || nodesToAdd.length > 5) {
      setTimeout(() => {
        if (networkRef.current) {
          networkRef.current.fit({ animation: true })
        }
      }, 100)
    }
    
    performance.mark('vis-data-conversion-end')
    performance.measure('vis-data-conversion', 'vis-data-conversion-start', 'vis-data-conversion-end')
  }, [])

  // Fetch graph data
  const fetchGraphData = useCallback(async (isInitialLoad = false) => {
    if (!activeServerId || !activeServer || activeServer.status !== 'connected') {
      setError('No active server connection')
      setLoading(false)
      return
    }

    try {
      // Only show loading on initial load
      if (isInitialLoad || nodeCount === 0) {
        setLoading(true)
      }
      setError(null)
      
      const graphData = await apiClient.getGraphData()
      
      if (!graphData) {
        throw new Error('No data received from server')
      }
      
      convertToVisData(graphData)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch graph data'
      setError(errorMessage)
      console.error('Error fetching graph data:', err)
    } finally {
      setLoading(false)
    }
  }, [activeServerId, activeServer, convertToVisData, nodeCount])

  // Initialize vis.js network
  useEffect(() => {
    if (!isMounted) {
      return
    }

    // Small delay to ensure DOM is ready
    const initTimer = setTimeout(() => {
      if (!containerRef.current) {
        return
      }

      // Check if container has dimensions
      const { offsetWidth, offsetHeight } = containerRef.current
      if (offsetWidth === 0 || offsetHeight === 0) {
        return
      }

      const options = layoutMode === 'physics' ? physicsOptions : hierarchicalOptions

      const data = {
        nodes: nodesDataSetRef.current,
        edges: edgesDataSetRef.current
      }
      console.log('Initial nodes count:', nodesDataSetRef.current.length)
      console.log('Initial edges count:', edgesDataSetRef.current.length)

      // Create network
      const network = new Network(containerRef.current, data, options)
      networkRef.current = network
      console.log('✅ Network created:', network)
      
      // Add click event handler
      network.on('click', (params) => {
        if (params.nodes.length > 0 && onNodeSelect) {
          const nodeId = params.nodes[0]
          const node = nodesDataSetRef.current.get(nodeId)
          
          if (node) {
            const nodeData = node as any
            if (nodeData.group === 'admin') {
              // Special handling for admin node
              onNodeSelect('admin', 'admin' as any, node)
            } else if (nodeData.group === 'agent' || nodeData.group === 'task' || nodeData.group === 'context' || nodeData.group === 'file') {
              onNodeSelect(nodeId, nodeData.group as 'agent' | 'task' | 'context' | 'file', node)
            }
          }
        }
      })
      
      // Add hover effect
      network.on('hoverNode', () => {
        containerRef.current!.style.cursor = 'pointer'
      })
      
      network.on('blurNode', () => {
        containerRef.current!.style.cursor = 'default'
      })
      
      // Force physics to start
      if (layoutMode === 'physics') {
        network.startSimulation()
        console.log('🏃 Physics simulation started')
      }

      // Add resize observer for responsive sizing
      const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          if (entry.target === containerRef.current && networkRef.current) {
            console.log('📐 Container resized:', entry.contentRect.width, 'x', entry.contentRect.height)
            // Redraw the network on resize
            networkRef.current.redraw()
            // Optionally fit to view after resize
            setTimeout(() => {
              networkRef.current?.fit({ animation: false })
            }, 100)
          }
        }
      })

      if (containerRef.current) {
        resizeObserver.observe(containerRef.current)
      }

      // Store cleanup function
      const cleanup = () => {
        resizeObserver.disconnect()
        if (networkRef.current) {
          networkRef.current.destroy()
          networkRef.current = null
        }
      }

      // Store cleanup in a ref for later use
      (window as any).__visCleanup = cleanup
    }, 100) // 100ms delay to ensure DOM is ready

    // Cleanup
    return () => {
      clearTimeout(initTimer)
      if ((window as any).__visCleanup) {
        (window as any).__visCleanup()
        delete (window as any).__visCleanup
      }
    }
  }, [layoutMode, isMounted])

  // Fetch data on mount and handle auto-refresh
  useEffect(() => {
    fetchGraphData(true) // Initial load

    if (autoRefresh) {
      const interval = setInterval(() => fetchGraphData(false), 30000) // 30 seconds, non-initial load
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


  return (
    <React.Profiler id="VisGraph" onRender={onVisGraphRender}>
      <div className={cn("w-full h-full flex", fullscreen ? "" : "graph-container rounded-lg border")}>
        {/* Main Content Area - Graph */}
        <div className="relative flex-1 min-w-0 bg-muted/20">
        {/* Controls Bar - Positioned over the graph */}
        <div className="absolute top-[var(--space-fluid-sm)] left-[var(--space-fluid-sm)] right-[var(--space-fluid-sm)] z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-[var(--space-fluid-xs)]">
          {/* Left side - Layout controls */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="bg-background/95 backdrop-blur rounded-lg border p-0.5 sm:p-1 flex gap-0.5 sm:gap-1">
              <Button
                variant={layoutMode === 'physics' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => handleLayoutChange('physics')}
                className="h-7 sm:h-8 px-2 sm:px-3 text-xs sm:text-sm"
              >
                <Layers className="h-3 sm:h-4 w-3 sm:w-4 mr-0.5 sm:mr-1" />
                <span className="hidden sm:inline">Physics</span>
                <span className="sm:hidden">P</span>
              </Button>
              <Button
                variant={layoutMode === 'hierarchical' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => handleLayoutChange('hierarchical')}
                className="h-7 sm:h-8 px-2 sm:px-3 text-xs sm:text-sm"
              >
                <GitBranch className="h-3 sm:h-4 w-3 sm:w-4 mr-0.5 sm:mr-1" />
                <span className="hidden sm:inline">Tree</span>
                <span className="sm:hidden">T</span>
              </Button>
            </div>
            
            <Badge variant="outline" className="bg-background/95 backdrop-blur text-xs sm:text-sm">
              <span className="hidden sm:inline">{nodeCount} nodes, {edgeCount} edges</span>
              <span className="sm:hidden">{nodeCount}n, {edgeCount}e</span>
            </Badge>
          </div>

          {/* Right side - Refresh controls */}
          <div className="flex items-center gap-1 sm:gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={cn("bg-background/95 backdrop-blur h-7 sm:h-8 px-2 sm:px-3 text-xs sm:text-sm", autoRefresh && "bg-primary/10")}
            >
              {autoRefresh ? (
                <>
                  <Activity className="h-3 sm:h-4 w-3 sm:w-4 mr-0.5 sm:mr-1 animate-pulse" />
                  <span className="hidden sm:inline">Live</span>
                </>
              ) : (
                <>
                  <RefreshCw className="h-3 sm:h-4 w-3 sm:w-4 mr-0.5 sm:mr-1" />
                  <span className="hidden sm:inline">Manual</span>
                </>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchGraphData(true)}
              disabled={loading}
              className="bg-background/95 backdrop-blur h-7 sm:h-8 px-2 sm:px-3"
            >
              {loading ? <RefreshCw className="h-3 sm:h-4 w-3 sm:w-4 animate-spin" /> : <RefreshCw className="h-3 sm:h-4 w-3 sm:w-4" />}
            </Button>
          </div>
        </div>

        {/* Graph Container */}
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
              <Activity className="h-12 w-12 mx-auto text-destructive" />
              <p className="text-muted-foreground">{error}</p>
              <Button onClick={() => fetchGraphData(true)} variant="outline">
                Retry
              </Button>
            </div>
          </div>
        ) : (
          <div 
            ref={containerRef} 
            className="w-full h-full" 
            onMouseEnter={() => console.log('🖱️ Mouse entered graph container')}
          />
        )}
        </div>
      </div>
    </React.Profiler>
  )
}