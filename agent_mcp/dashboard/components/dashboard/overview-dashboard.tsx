"use client"

import React, { useState, useEffect, useCallback, useMemo } from "react"
import { Activity, Users, CheckSquare, TrendingUp, Zap, Server, RefreshCw } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { apiClient, SystemStatus } from "@/lib/api"
import { useServerStore } from "@/lib/stores/server-store"

// Cache for system status data
const systemCache = new Map<string, { data: SystemStatus, timestamp: number }>()
const CACHE_DURATION = 30000 // 30 seconds
const REFRESH_INTERVAL = 60000 // 1 minute for background refresh

// Real data hook for system status with caching
const useSystemData = () => {
  const { activeServerId, servers } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  
  const [data, setData] = useState<SystemStatus>({
    server_running: false,
    total_agents: 0,
    active_agents: 0,
    total_tasks: 0,
    completed_tasks: 0,
    pending_tasks: 0,
    last_updated: ""
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastFetch, setLastFetch] = useState<number>(0)

  const fetchData = useCallback(async (forceRefresh = false) => {
    if (!activeServerId || !activeServer || activeServer.status !== 'connected') {
      setData({
        server_running: false,
        total_agents: 0,
        active_agents: 0,
        total_tasks: 0,
        completed_tasks: 0,
        pending_tasks: 0,
        last_updated: ""
      })
      setError(null)
      setLoading(false)
      return
    }

    const cacheKey = `${activeServerId}-system`
    const now = Date.now()
    const cached = systemCache.get(cacheKey)

    // Use cache if it's fresh and not forcing refresh
    if (!forceRefresh && cached && (now - cached.timestamp) < CACHE_DURATION) {
      setData(cached.data)
      setError(null)
      setLoading(false)
      return
    }

    // Only show loading on first fetch or force refresh
    if (!data.server_running || forceRefresh) {
      setLoading(true)
    }

    try {
      const status = await apiClient.getSystemStatus()
      
      // Update cache
      systemCache.set(cacheKey, { data: status, timestamp: now })
      
      setData(status)
      setError(null)
      setLastFetch(now)
    } catch (err) {
      // Don't set error state for no server connection - that's handled by DashboardWrapper
      if (err instanceof Error && err.message !== 'NO_SERVER_CONNECTED') {
        setError(err.message)
        console.error('Error fetching system status:', err)
      }
    } finally {
      setLoading(false)
    }
  }, [activeServerId, activeServer, data.server_running])

  useEffect(() => {
    fetchData()
    
    // Background refresh - less frequent and doesn't show loading
    const interval = setInterval(() => {
      fetchData(false)
    }, REFRESH_INTERVAL)
    
    return () => clearInterval(interval)
  }, [fetchData])

  // Manual refresh function
  const refresh = useCallback(() => fetchData(true), [fetchData])

  // Memoize return value to prevent unnecessary re-renders
  return useMemo(() => ({
    data, 
    loading, 
    error, 
    refresh,
    lastFetch,
    isConnected: !!activeServerId && activeServer?.status === 'connected' 
  }), [data, loading, error, refresh, lastFetch, activeServerId, activeServer])
}

const StatCard = React.memo(({ 
  title, 
  value, 
  description, 
  icon: Icon, 
  change, 
  changeType = "positive" 
}: {
  title: string
  value: string | number
  description: string
  icon: React.ComponentType<{ className?: string }>
  change?: string
  changeType?: "positive" | "negative" | "neutral"
}) => {
  const changeColors = {
    positive: "text-teal-600 dark:text-teal-400",
    negative: "text-orange-600 dark:text-orange-400", 
    neutral: "text-muted-foreground"
  }

  return (
    <Card className="bg-card/80 border border-border/60 rounded-xl backdrop-blur-sm hover:bg-card transition-all duration-200 group">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-foreground mb-1">{value}</div>
        <div className="flex items-center space-x-2">
          <p className="text-xs text-muted-foreground">{description}</p>
          {change && (
            <span className={`text-xs font-medium ${changeColors[changeType]}`}>
              {change}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
})
StatCard.displayName = 'StatCard'

export function OverviewDashboard() {
  const [mounted, setMounted] = useState(false)
  const { data: systemData, loading, error, isConnected, refresh, lastFetch } = useSystemData()
  const { servers, activeServerId } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  
  useEffect(() => {
    setMounted(true)
  }, [])
  
  const completionRate = systemData.total_tasks > 0 ? Math.round((systemData.completed_tasks / systemData.total_tasks) * 100) : 0
  const agentUtilization = systemData.total_agents > 0 ? Math.round((systemData.active_agents / systemData.total_agents) * 100) : 0

  // Show connection prompt if no server is selected
  if (!isConnected) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
            <p className="text-muted-foreground">System dashboard and performance metrics</p>
          </div>
          <Badge variant="secondary">
            <Server className="w-4 h-4 mr-2" />
            No Server Connected
          </Badge>
        </div>

        <Card className="bg-card border border-border rounded-xl">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Server className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">Connect to an MCP Server</h3>
            <p className="text-muted-foreground text-center mb-4">
              Select an MCP server from the project picker in the header to view system metrics and manage agents.
            </p>
            {activeServer && activeServer.status === 'error' && (
              <div className="text-sm text-destructive">
                Failed to connect to {activeServer.name} ({activeServer.host}:{activeServer.port})
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
            <p className="text-muted-foreground">Loading system data...</p>
          </div>
          <Badge variant="outline">
            <div className="w-2 h-2 bg-blue-500 rounded-full mr-2 animate-pulse"></div>
            Connecting
          </Badge>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="bg-card border border-border rounded-xl">
              <CardContent className="p-6">
                <div className="animate-pulse">
                  <div className="h-4 bg-muted rounded w-1/2 mb-2"></div>
                  <div className="h-8 bg-muted rounded w-1/3 mb-2"></div>
                  <div className="h-3 bg-muted rounded w-2/3"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
            <p className="text-destructive">Error loading system data: {error}</p>
          </div>
          <Badge variant="destructive">
            <div className="w-2 h-2 bg-red-500 rounded-full mr-2"></div>
            Connection Error
          </Badge>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">System Overview</h1>
          <p className="text-muted-foreground text-sm">
            Real-time autonomous system monitoring and analytics
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className={systemData.server_running ? "bg-primary/15 text-primary border-primary/30" : "bg-destructive/15 text-destructive border-destructive/30"}>
            <div className={`w-2 h-2 rounded-full mr-2 ${systemData.server_running ? 'bg-primary animate-pulse' : 'bg-destructive animate-pulse'}`}></div>
            {systemData.server_running ? 'Server Online' : 'Server Offline'}
          </Badge>
          <Badge variant="outline" className="bg-muted/50 text-muted-foreground border-border">
            <Server className="w-4 h-4 mr-2" />
            {activeServer?.name}
          </Badge>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={refresh}
            disabled={loading}
            className="border-primary/30 text-primary hover:bg-primary/10"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Agents"
          value={systemData.total_agents}
          description="Registered in system"
          icon={Users}
        />
        <StatCard
          title="Active Agents"
          value={systemData.active_agents}
          description="Currently running"
          icon={Zap}
        />
        <StatCard
          title="Total Tasks"
          value={systemData.total_tasks}
          description="All time created"
          icon={CheckSquare}
        />
        <StatCard
          title="Completion Rate"
          value={`${completionRate}%`}
          description="Tasks completed"
          icon={TrendingUp}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* System Health */}
        <Card className="bg-card border border-border rounded-xl lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-foreground">System Health</CardTitle>
            <CardDescription className="text-muted-foreground">
              Current system performance and resource utilization
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-foreground">Agent Utilization</span>
                <span className="text-primary font-semibold">{agentUtilization}%</span>
              </div>
              <Progress value={agentUtilization} className="h-3" />
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-foreground">Task Completion</span>
                <span className="text-primary font-semibold">{completionRate}%</span>
              </div>
              <Progress value={completionRate} className="h-3" />
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-foreground">System Uptime</span>
                <span className="text-primary font-semibold">{systemData.systemUptime}</span>
              </div>
              <Progress value={parseFloat(systemData.systemUptime)} className="h-3" />
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="bg-card border border-border rounded-xl">
          <CardHeader>
            <CardTitle className="text-foreground">Quick Actions</CardTitle>
            <CardDescription className="text-muted-foreground">
              Common operations and shortcuts
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button className="w-full justify-start bg-primary hover:bg-primary/90 text-primary-foreground">
              <Users className="h-4 w-4 mr-2" />
              Create New Agent
            </Button>
            <Button className="w-full justify-start" variant="outline">
              <CheckSquare className="h-4 w-4 mr-2" />
              Add Task
            </Button>
            <Button className="w-full justify-start" variant="outline">
              <Activity className="h-4 w-4 mr-2" />
              View Logs
            </Button>
            <Button className="w-full justify-start" variant="outline">
              <TrendingUp className="h-4 w-4 mr-2" />
              Analytics
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card className="bg-card border border-border rounded-xl">
        <CardHeader>
          <CardTitle className="text-foreground">Recent Activity</CardTitle>
          <CardDescription className="text-muted-foreground">
            Latest system events and updates
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <Activity className="h-8 w-8 mx-auto mb-2 text-muted-foreground opacity-50" />
            <p className="text-muted-foreground">No recent activity available</p>
            <p className="text-sm text-muted-foreground">Activity will appear here when agents start working</p>
          </div>
        </CardContent>
      </Card>

      {/* Footer */}
      <div className="text-center text-sm text-muted-foreground">
        {mounted ? `Last updated: ${lastFetch ? new Date(lastFetch).toLocaleTimeString() : systemData.last_updated || new Date().toLocaleTimeString()}` : "Loading..."}
      </div>
    </div>
  )
}