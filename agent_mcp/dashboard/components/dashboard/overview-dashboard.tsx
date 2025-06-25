"use client"

import React from "react"
import { Activity, Users, CheckSquare, Clock, TrendingUp, Zap } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"

// Mock data - this will be replaced with real API data
const mockData = {
  totalAgents: 12,
  activeAgents: 8,
  totalTasks: 45,
  completedTasks: 32,
  pendingTasks: 13,
  systemUptime: "99.8%",
  lastUpdate: new Date().toLocaleString()
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
  const completionRate = Math.round((mockData.completedTasks / mockData.totalTasks) * 100)
  const agentUtilization = Math.round((mockData.activeAgents / mockData.totalAgents) * 100)

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
          value={mockData.totalAgents}
          description="Registered in system"
          icon={Users}
          change="+2 this week"
          changeType="positive"
        />
        <StatCard
          title="Active Agents"
          value={mockData.activeAgents}
          description="Currently running"
          icon={Zap}
          change={`${agentUtilization}% utilization`}
          changeType="neutral"
        />
        <StatCard
          title="Total Tasks"
          value={mockData.totalTasks}
          description="All time created"
          icon={CheckSquare}
          change="+8 today"
          changeType="positive"
        />
        <StatCard
          title="Completion Rate"
          value={`${completionRate}%`}
          description="Tasks completed"
          icon={TrendingUp}
          change="+5% this week"
          changeType="positive"
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
                <span>{mockData.systemUptime}</span>
              </div>
              <Progress value={99.8} className="h-2" />
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
          <div className="space-y-3">
            {[
              { 
                action: "Agent 'data-processor' completed task",
                time: "2 minutes ago",
                type: "success"
              },
              { 
                action: "New task 'analyze-metrics' created",
                time: "5 minutes ago",
                type: "info"
              },
              { 
                action: "Agent 'web-scraper' started",
                time: "12 minutes ago",
                type: "info"
              },
              { 
                action: "Task 'backup-database' failed",
                time: "1 hour ago",
                type: "error"
              }
            ].map((activity, index) => (
              <div key={index} className="flex items-center justify-between py-2 border-b last:border-b-0">
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 rounded-full ${
                    activity.type === 'success' ? 'bg-green-500' :
                    activity.type === 'error' ? 'bg-red-500' : 'bg-blue-500'
                  }`} />
                  <span className="text-sm">{activity.action}</span>
                </div>
                <span className="text-xs text-muted-foreground">{activity.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Footer */}
      <div className="text-center text-sm text-muted-foreground">
        Last updated: {mockData.lastUpdate}
      </div>
    </div>
  )
}