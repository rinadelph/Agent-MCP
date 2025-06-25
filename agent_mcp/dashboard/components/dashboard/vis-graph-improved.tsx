"use client"

import React, { useEffect, useRef, useCallback, useState } from 'react'
import { Network, DataSet } from 'vis-network/standalone'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  RefreshCw, GitBranch, Activity, Layers
} from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useServerStore } from '@/lib/stores/server-store'
import { cn } from '@/lib/utils'

// Physics options optimized for cluster-based layout
const physicsOptions = {
  physics: {
    enabled: true,
    barnesHut: {
      gravitationalConstant: -8000, // Moderate repulsion
      centralGravity: 0.03, // Slight central gravity
      springLength: 200, // Reasonable spring length
      springConstant: 0.02, // Soft springs
      damping: 0.3, // Good damping for stability
      avoidOverlap: 0.8 // Good overlap avoidance
    },
    maxVelocity: 40,
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
}

export function VisGraphImproved({ fullscreen = false }: VisGraphProps) {
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

  // Convert API data to vis.js format with improved clustering
  const convertToVisData = useCallback((graphData: any) => {
    if (!graphData || !graphData.nodes || !graphData.edges) {
      console.warn('Invalid graph data structure:', graphData)
      return
    }

    // Get current nodes and edges
    const currentNodeIds = new Set(nodesDataSetRef.current.getIds())
    const currentEdgeIds = new Set(edgesDataSetRef.current.getIds())

    // Build adjacency map
    const adjacencyMap = new Map<string, Set<string>>()
    graphData.edges.forEach((edge: any) => {
      if (!adjacencyMap.has(edge.from)) adjacencyMap.set(edge.from, new Set())
      if (!adjacencyMap.has(edge.to)) adjacencyMap.set(edge.to, new Set())
      adjacencyMap.get(edge.from)!.add(edge.to)
      adjacencyMap.get(edge.to)!.add(edge.from)
    })

    // Filter out idle agents
    const filteredNodes = graphData.nodes.filter((node: any) => {
      if (node.group === 'admin') return true
      if (node.group !== 'agent') return true
      return adjacencyMap.has(node.id)
    })

    // Identify clusters: each agent and its connected nodes
    const clusters = new Map<string, {
      agent: any,
      contexts: any[],
      tasks: any[],
      files: any[]
    }>()
    
    // Separate admin's context nodes for special handling
    const adminContexts: any[] = []

    // First, identify all agents
    const agentNodes = filteredNodes.filter((n: any) => n.group === 'agent')
    agentNodes.forEach((agent: any) => {
      clusters.set(agent.id, {
        agent,
        contexts: [],
        tasks: [],
        files: []
      })
    })

    // Assign nodes to their nearest agent cluster
    filteredNodes.forEach((node: any) => {
      if (node.group === 'admin' || node.group === 'agent') return
      
      // Check if this is connected to admin
      let isConnectedToAdmin = false
      graphData.edges.forEach((edge: any) => {
        if ((edge.from === node.id && filteredNodes.find((n: any) => n.id === edge.to && n.group === 'admin')) ||
            (edge.to === node.id && filteredNodes.find((n: any) => n.id === edge.from && n.group === 'admin'))) {
          isConnectedToAdmin = true
        }
      })
      
      // If it's a context node connected to admin, handle separately
      if (node.group === 'context' && isConnectedToAdmin) {
        adminContexts.push(node)
        return
      }
      
      // Find which agents this node is connected to
      const connectedAgents = new Set<string>()
      graphData.edges.forEach((edge: any) => {
        if (edge.from === node.id && clusters.has(edge.to)) {
          connectedAgents.add(edge.to)
        } else if (edge.to === node.id && clusters.has(edge.from)) {
          connectedAgents.add(edge.from)
        }
      })

      // Add to the first connected agent's cluster
      if (connectedAgents.size > 0) {
        const agentId = Array.from(connectedAgents)[0]
        const cluster = clusters.get(agentId)!
        if (node.group === 'context') cluster.contexts.push(node)
        else if (node.group === 'task') cluster.tasks.push(node)
        else if (node.group === 'file') cluster.files.push(node)
      }
    })

    // Position nodes with improved clustering
    const visNodes: any[] = []
    
    // Admin node at center
    const adminNode = filteredNodes.find((n: any) => n.group === 'admin')
    if (adminNode) {
      const styling = getNodeStyling(adminNode)
      visNodes.push({
        id: adminNode.id,
        label: adminNode.label || adminNode.id,
        title: `${adminNode.group}: ${adminNode.label}`,
        group: adminNode.group,
        fixed: { x: true, y: true },
        x: 0,
        y: 0,
        physics: false,
        ...styling,
        ...adminNode
      })
    }
    
    // Position admin's context nodes in a crown with moderate repelling
    const adminContextRadius = 400 // Large radius to create space
    adminContexts.forEach((context, index) => {
      const angle = (index * 2 * Math.PI) / adminContexts.length
      const x = Math.cos(angle) * adminContextRadius
      const y = Math.sin(angle) * adminContextRadius
      
      const ctxStyling = getNodeStyling(context)
      visNodes.push({
        id: context.id,
        label: context.label || context.id,
        title: `${context.group}: ${context.label}`,
        group: context.group,
        x: x,
        y: y,
        fixed: { x: true, y: true }, // Fix position to maintain crown
        physics: false, // Disable physics for stable crown
        mass: 10, // Moderate mass if physics gets enabled
        ...ctxStyling,
        ...context
      })
    })

    // Position agent clusters with improved spacing, outside admin context crown
    const clusterArray = Array.from(clusters.values())
    const numClusters = clusterArray.length
    const minClusterRadius = adminContextRadius + 250 // Reasonable spacing from admin crown
    const baseRadius = Math.max(minClusterRadius, numClusters * 120) // Dynamic radius based on cluster count
    
    clusterArray.forEach((cluster, index) => {
      // Use golden angle for better distribution
      const goldenAngle = Math.PI * (3 - Math.sqrt(5))
      const angle = index * goldenAngle
      const clusterCenterX = Math.cos(angle) * baseRadius
      const clusterCenterY = Math.sin(angle) * baseRadius
      
      // Position agent
      const agentStyling = getNodeStyling(cluster.agent)
      visNodes.push({
        id: cluster.agent.id,
        label: cluster.agent.label || cluster.agent.id,
        title: `${cluster.agent.group}: ${cluster.agent.label}`,
        group: cluster.agent.group,
        x: clusterCenterX,
        y: clusterCenterY,
        ...agentStyling,
        ...cluster.agent
      })
      
      // Position context nodes in a crown around the agent with better spacing
      const contextRadius = 200 // Increased radius for better spacing
      const contextAngleOffset = angle // Align context crown with cluster angle
      cluster.contexts.forEach((context, ctxIndex) => {
        const ctxAngle = contextAngleOffset + (ctxIndex * 2 * Math.PI) / cluster.contexts.length
        const ctxX = clusterCenterX + Math.cos(ctxAngle) * contextRadius
        const ctxY = clusterCenterY + Math.sin(ctxAngle) * contextRadius
        
        const ctxStyling = getNodeStyling(context)
        visNodes.push({
          id: context.id,
          label: context.label || context.id,
          title: `${context.group}: ${context.label}`,
          group: context.group,
          x: ctxX,
          y: ctxY,
          fixed: { x: true, y: true },
          physics: false,
          ...ctxStyling,
          ...context
        })
      })
      
      // Position task nodes in a second ring with better distribution
      const taskRadius = 350 // Increased for better spacing
      const taskAngleOffset = angle + Math.PI / 6 // Offset from context nodes
      cluster.tasks.forEach((task, taskIndex) => {
        const taskAngle = taskAngleOffset + (taskIndex * 2 * Math.PI) / cluster.tasks.length
        const taskX = clusterCenterX + Math.cos(taskAngle) * taskRadius
        const taskY = clusterCenterY + Math.sin(taskAngle) * taskRadius
        
        const taskStyling = getNodeStyling(task)
        visNodes.push({
          id: task.id,
          label: task.label || task.id,
          title: `${task.group}: ${task.label}`,
          group: task.group,
          x: taskX,
          y: taskY,
          ...taskStyling,
          ...task
        })
      })
      
      // Position file nodes in inner ring with spiral pattern for better distribution
      const fileBaseRadius = 150
      const fileAngleOffset = angle - Math.PI / 4 // Different offset from other nodes
      cluster.files.forEach((file, fileIndex) => {
        // Spiral pattern for files if there are many
        const spiralFactor = cluster.files.length > 4 ? fileIndex * 20 : 0
        const fileRadius = fileBaseRadius + spiralFactor
        const fileAngle = fileAngleOffset + (fileIndex * 2 * Math.PI) / cluster.files.length
        const fileX = clusterCenterX + Math.cos(fileAngle) * fileRadius
        const fileY = clusterCenterY + Math.sin(fileAngle) * fileRadius
        
        const fileStyling = getNodeStyling(file)
        visNodes.push({
          id: file.id,
          label: file.label || file.id,
          title: `${file.group}: ${file.label}`,
          group: file.group,
          x: fileX,
          y: fileY,
          ...fileStyling,
          ...file
        })
      })
    })
    
    // Add any unassigned nodes
    filteredNodes.forEach((node: any) => {
      if (!visNodes.find((vn: any) => vn.id === node.id)) {
        const styling = getNodeStyling(node)
        visNodes.push({
          id: node.id,
          label: node.label || node.id,
          title: `${node.group}: ${node.label}`,
          group: node.group,
          ...styling,
          ...node
        })
      }
    })

    // Convert edges
    const visEdges = graphData.edges.map((edge: any, index: number) => {
      let edgeStyle: any = {
        from: edge.from,
        to: edge.to,
        id: edge.id || `edge-${index}`,
        arrows: edge.arrows || { to: { enabled: true, scaleFactor: 0.5 } }
      }

      // Apply edge styling based on type
      if (edge.title) {
        edgeStyle.title = edge.title
        
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
      
      // Inter-cluster edges should be more curved to avoid crossing
      const fromNode = visNodes.find((n: any) => n.id === edge.from)
      const toNode = visNodes.find((n: any) => n.id === edge.to)
      if (fromNode && toNode) {
        const fromCluster = Array.from(clusters.entries()).find(([_, cluster]) => 
          cluster.agent.id === fromNode.id || 
          cluster.contexts.some((c: any) => c.id === fromNode.id) ||
          cluster.tasks.some((t: any) => t.id === fromNode.id) ||
          cluster.files.some((f: any) => f.id === fromNode.id)
        )
        const toCluster = Array.from(clusters.entries()).find(([_, cluster]) => 
          cluster.agent.id === toNode.id || 
          cluster.contexts.some((c: any) => c.id === toNode.id) ||
          cluster.tasks.some((t: any) => t.id === toNode.id) ||
          cluster.files.some((f: any) => f.id === toNode.id)
        )
        
        // If nodes are in different clusters, make edge more curved
        if (fromCluster && toCluster && fromCluster[0] !== toCluster[0]) {
          edgeStyle.smooth = { enabled: true, type: 'curvedCW', roundness: 0.6 }
          edgeStyle.color = { ...edgeStyle.color, opacity: 0.5 }
        }
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
    <div className={cn("relative w-full bg-background", fullscreen ? "h-full" : "graph-container rounded-lg border")}>
      {/* Controls Bar */}
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
          className="w-full h-full bg-muted/20" 
          onMouseEnter={() => console.log('🖱️ Mouse entered graph container')}
        />
      )}
    </div>
  )
}