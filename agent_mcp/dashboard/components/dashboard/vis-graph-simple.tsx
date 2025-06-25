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
      borderWidth: 2,
      color: { background: '#9C27B0', border: '#7B1FA2' }
    },
    file: {
      shape: 'triangle',
      borderWidth: 2,
      color: { background: '#795548', border: '#5D4037' }
    },
    admin: {
      shape: 'star',
      borderWidth: 3,
      color: { background: '#607D8B', border: '#455A64' }
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
  const [nodeCount, setNodeCount] = useState(0)
  const [edgeCount, setEdgeCount] = useState(0)
  const [isMounted, setIsMounted] = useState(false)
  
  // Track mounted state
  useEffect(() => {
    console.log('🚀 VisGraph mounted with props:', { fullscreen })
    setIsMounted(true)
    return () => {
      console.log('🔚 VisGraph unmounted')
      setIsMounted(false)
    }
  }, [])

  // Convert API data to vis.js format
  const convertToVisData = useCallback((graphData: any) => {
    if (!graphData || !graphData.nodes || !graphData.edges) {
      console.warn('Invalid graph data structure:', graphData)
      return
    }

    console.log(`Converting ${graphData.nodes.length} nodes and ${graphData.edges.length} edges`)

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
        }
      }

      // Apply any custom edge properties from the API
      if (edge.color) edgeStyle.color = edge.color
      if (edge.width) edgeStyle.width = edge.width

      return edgeStyle
    })

    // Update datasets
    console.log('📝 Clearing and updating datasets...')
    nodesDataSetRef.current.clear()
    nodesDataSetRef.current.add(visNodes)
    edgesDataSetRef.current.clear()
    edgesDataSetRef.current.add(visEdges)
    
    console.log('✅ Datasets updated:')
    console.log('  - Nodes in dataset:', nodesDataSetRef.current.length)
    console.log('  - Edges in dataset:', edgesDataSetRef.current.length)
    console.log('  - Sample nodes:', nodesDataSetRef.current.get().slice(0, 3))

    setNodeCount(visNodes.length)
    setEdgeCount(visEdges.length)

    // Fit network to view
    setTimeout(() => {
      if (networkRef.current) {
        networkRef.current.fit({ animation: true })
        console.log('🎯 Fit to view executed')
        const positions = networkRef.current.getPositions()
        console.log('Network positions sample:', Object.keys(positions).slice(0, 3).map(id => ({ id, pos: positions[id] })))
      } else {
        console.error('❌ Network ref is null during fit!')
      }
    }, 100)
  }, [])

  // Fetch graph data
  const fetchGraphData = useCallback(async () => {
    if (!activeServerId || !activeServer || activeServer.status !== 'connected') {
      setError('No active server connection')
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)
      
      const graphData = await apiClient.getGraphData()
      
      if (!graphData) {
        throw new Error('No data received from server')
      }
      
      console.log('📊 Graph data received:', {
        nodes: graphData.nodes?.length || 0,
        edges: graphData.edges?.length || 0,
        sampleNode: graphData.nodes?.[0],
        sampleEdge: graphData.edges?.[0]
      })
      convertToVisData(graphData)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch graph data'
      setError(errorMessage)
      console.error('Error fetching graph data:', err)
    } finally {
      setLoading(false)
    }
  }, [activeServerId, activeServer, convertToVisData])

  // Initialize vis.js network
  useEffect(() => {
    if (!isMounted) {
      return
    }

    // Small delay to ensure DOM is ready
    const initTimer = setTimeout(() => {
      console.log('🔧 Initializing vis.js network...')
      console.log('Container ref:', containerRef.current)
      console.log('Container dimensions:', containerRef.current?.offsetWidth, 'x', containerRef.current?.offsetHeight)
      
      if (!containerRef.current) {
        console.warn('⚠️ Container ref is not ready yet')
        return
      }

      // Check if container has dimensions
      const { offsetWidth, offsetHeight } = containerRef.current
      if (offsetWidth === 0 || offsetHeight === 0) {
        console.warn('⚠️ Container has no dimensions yet')
        return
      }

      const options = layoutMode === 'physics' ? physicsOptions : hierarchicalOptions
      console.log('Layout mode:', layoutMode)

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
            onClick={fetchGraphData}
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
            <Button onClick={fetchGraphData} variant="outline">
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