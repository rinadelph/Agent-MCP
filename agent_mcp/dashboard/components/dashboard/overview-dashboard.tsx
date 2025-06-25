"use client"

import React, { useState, useEffect } from "react"
import { Activity, Users, CheckSquare, TrendingUp, Zap } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"

// Real data hooks - will be populated by API calls
const useSystemData = () => {
  const [data, setData] = useState({
    totalAgents: 0,
    activeAgents: 0,
    totalTasks: 0,
    completedTasks: 0,
    pendingTasks: 0,
    systemUptime: "0%"
  })

  useEffect(() => {
    // TODO: Fetch real data from API
    // This will be replaced with actual API calls
    setData({
      totalAgents: 0,
      activeAgents: 0,
      totalTasks: 0,
      completedTasks: 0,
      pendingTasks: 0,
      systemUptime: "0%"
    })
  }, [])

  return data
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
  const [lastUpdate, setLastUpdate] = useState<string>("")
  const [mounted, setMounted] = useState(false)
  const systemData = useSystemData()
  
  useEffect(() => {
    setMounted(true)
    setLastUpdate(new Date().toLocaleString())
  }, [])
  
  const completionRate = systemData.totalTasks > 0 ? Math.round((systemData.completedTasks / systemData.totalTasks) * 100) : 0
  const agentUtilization = systemData.totalAgents > 0 ? Math.round((systemData.activeAgents / systemData.totalAgents) * 100) : 0

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
          <Badge variant="outline" className="status-online">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            System Online
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
          value={systemData.totalAgents}
          description="Registered in system"
          icon={Users}
        />
        <StatCard
          title="Active Agents"
          value={systemData.activeAgents}
          description="Currently running"
          icon={Zap}
        />
        <StatCard
          title="Total Tasks"
          value={systemData.totalTasks}
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
        {mounted ? `Last updated: ${lastUpdate}` : "Loading..."}
      </div>
    </div>
  )
}