"use client"

import React, { useState, useEffect } from "react"
import { Activity, Users, CheckSquare, TrendingUp, Zap, Server } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { apiClient, SystemStatus } from "@/lib/api"
import { useServerStore } from "@/lib/stores/server-store"

// Real data hook for system status
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

  useEffect(() => {
    // Don't fetch if no server is connected
    if (!activeServerId || !activeServer || activeServer.status !== 'connected') {
      setLoading(false)
      setError(null)
      return
    }

    const fetchData = async () => {
      setLoading(true)
      try {
        const status = await apiClient.getSystemStatus()
        setData(status)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch system status')
        console.error('Error fetching system status:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    
    // Set up polling for real-time updates only when connected
    const interval = setInterval(fetchData, 10000) // Update every 10 seconds
    
    return () => clearInterval(interval)
  }, [activeServerId, activeServer])

  return { data, loading, error, isConnected: !!activeServerId && activeServer?.status === 'connected' }
}

const StatCard = ({ 
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
    positive: "text-green-600 dark:text-green-400",
    negative: "text-red-600 dark:text-red-400", 
    neutral: "text-muted-foreground"
  }

  return (
    <Card className="card-premium">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="flex items-center space-x-2">
          <p className="text-xs text-muted-foreground">{description}</p>
          {change && (
            <span className={`text-xs ${changeColors[changeType]}`}>
              {change}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function OverviewDashboard() {
  const [mounted, setMounted] = useState(false)
  const { data: systemData, loading, error, isConnected } = useSystemData()
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

        <Card className="card-premium">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Server className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">Connect to an MCP Server</h3>
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
            <Card key={i} className="card-premium">
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
          <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
          <p className="text-muted-foreground">
            System dashboard and performance metrics
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className={systemData.server_running ? "status-online" : "status-error"}>
            <div className={`w-2 h-2 rounded-full mr-2 ${systemData.server_running ? 'bg-green-500' : 'bg-red-500'}`}></div>
            {systemData.server_running ? 'Server Online' : 'Server Offline'}
          </Badge>
          <Badge variant="secondary">
            <Server className="w-4 h-4 mr-2" />
            {activeServer?.name}
          </Badge>
          <Button variant="outline" size="sm">
            <Activity className="h-4 w-4 mr-2" />
            Real-time
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
        <Card className="card-premium lg:col-span-2">
          <CardHeader>
            <CardTitle>System Health</CardTitle>
            <CardDescription>
              Current system performance and resource utilization
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Agent Utilization</span>
                <span>{agentUtilization}%</span>
              </div>
              <Progress value={agentUtilization} className="h-2" />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Task Completion</span>
                <span>{completionRate}%</span>
              </div>
              <Progress value={completionRate} className="h-2" />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>System Uptime</span>
                <span>{systemData.systemUptime}</span>
              </div>
              <Progress value={parseFloat(systemData.systemUptime)} className="h-2" />
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="card-premium">
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common operations and shortcuts
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button className="w-full justify-start" variant="outline">
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
      <Card className="card-premium">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>
            Latest system events and updates
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No recent activity available</p>
            <p className="text-sm">Activity will appear here when agents start working</p>
          </div>
        </CardContent>
      </Card>

      {/* Footer */}
      <div className="text-center text-sm text-muted-foreground">
        {mounted ? `Last updated: ${systemData.last_updated || new Date().toLocaleTimeString()}` : "Loading..."}
      </div>
    </div>
  )
}