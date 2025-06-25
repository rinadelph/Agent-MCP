"use client"

import React from "react"
import { SystemGraph } from "./system-graph"
import { TestGraph } from "./test-graph"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { 
  Activity, Database, FileText, GitBranch, 
  Shield, Cpu, HardDrive, Network, Clock,
  AlertCircle, CheckCircle2, Info, XCircle
} from "lucide-react"
import { useServerStore } from "@/lib/stores/server-store"

// System metrics component
const SystemMetrics = () => {
  const { activeServerId, servers } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)

  if (!activeServer || activeServer.status !== 'connected') {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map(i => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <div className="h-4 bg-muted rounded w-24" />
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-muted rounded w-16 mb-2" />
              <div className="h-3 bg-muted rounded w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const metrics = [
    {
      title: "CPU Usage",
      value: "45%",
      icon: Cpu,
      trend: "stable",
      color: "text-blue-600"
    },
    {
      title: "Memory",
      value: "2.4GB",
      icon: HardDrive,
      trend: "up",
      color: "text-green-600"
    },
    {
      title: "Active Connections",
      value: "12",
      icon: Network,
      trend: "up",
      color: "text-purple-600"
    },
    {
      title: "Response Time",
      value: "120ms",
      icon: Clock,
      trend: "down",
      color: "text-orange-600"
    }
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {metrics.map((metric, index) => (
        <Card key={index}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              {metric.title}
            </CardTitle>
            <metric.icon className={cn("h-4 w-4", metric.color)} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metric.value}</div>
            <p className="text-xs text-muted-foreground">
              {metric.trend === 'up' && '↑'}
              {metric.trend === 'down' && '↓'}
              {metric.trend === 'stable' && '→'}
              {' '}from last hour
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// System logs component
const SystemLogs = () => {
  const logs = [
    {
      timestamp: new Date().toISOString(),
      level: 'info',
      message: 'System initialized successfully',
      source: 'core'
    },
    {
      timestamp: new Date(Date.now() - 300000).toISOString(),
      level: 'warning',
      message: 'High memory usage detected',
      source: 'monitor'
    },
    {
      timestamp: new Date(Date.now() - 600000).toISOString(),
      level: 'error',
      message: 'Failed to connect to external service',
      source: 'api'
    },
    {
      timestamp: new Date(Date.now() - 900000).toISOString(),
      level: 'success',
      message: 'Database backup completed',
      source: 'backup'
    }
  ]

  const levelIcons: { [key: string]: React.ReactNode } = {
    info: <Info className="h-4 w-4 text-blue-600" />,
    warning: <AlertCircle className="h-4 w-4 text-yellow-600" />,
    error: <XCircle className="h-4 w-4 text-red-600" />,
    success: <CheckCircle2 className="h-4 w-4 text-green-600" />
  }

  const levelColors: { [key: string]: string } = {
    info: 'text-blue-600 bg-blue-50',
    warning: 'text-yellow-600 bg-yellow-50',
    error: 'text-red-600 bg-red-50',
    success: 'text-green-600 bg-green-50'
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>System Logs</CardTitle>
        <CardDescription>Recent system events and activities</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {logs.map((log, index) => (
            <div key={index} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30">
              {levelIcons[log.level]}
              <div className="flex-1 space-y-1">
                <p className="text-sm">{log.message}</p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span>•</span>
                  <span>{log.source}</span>
                </div>
              </div>
              <Badge variant="secondary" className={cn("text-xs", levelColors[log.level])}>
                {log.level}
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// Resource usage component
const ResourceUsage = () => {
  const resources = [
    { name: "Database Storage", used: 45, total: 100, unit: "GB" },
    { name: "RAG Embeddings", used: 12000, total: 50000, unit: "vectors" },
    { name: "API Requests", used: 8500, total: 10000, unit: "req/day" },
    { name: "Agent Slots", used: 8, total: 12, unit: "agents" }
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Resource Usage</CardTitle>
        <CardDescription>System resource allocation and limits</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {resources.map((resource, index) => (
          <div key={index} className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="font-medium">{resource.name}</span>
              <span className="text-muted-foreground">
                {resource.used.toLocaleString()} / {resource.total.toLocaleString()} {resource.unit}
              </span>
            </div>
            <Progress value={(resource.used / resource.total) * 100} className="h-2" />
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

// Main System Dashboard
export function SystemDashboard() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">System</h1>
          <p className="text-muted-foreground">
            System architecture, performance metrics, and health monitoring
          </p>
        </div>
        <Badge variant="outline" className="status-online">
          <Activity className="h-3 w-3 mr-1" />
          All Systems Operational
        </Badge>
      </div>

      {/* System Metrics */}
      <SystemMetrics />

      {/* Main Content */}
      <Tabs defaultValue="graph" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="graph">
            <Network className="h-4 w-4 mr-2" />
            System Graph
          </TabsTrigger>
          <TabsTrigger value="test">
            Test Graph
          </TabsTrigger>
          <TabsTrigger value="resources">
            <Database className="h-4 w-4 mr-2" />
            Resources
          </TabsTrigger>
          <TabsTrigger value="logs">
            <FileText className="h-4 w-4 mr-2" />
            Logs
          </TabsTrigger>
        </TabsList>

        <TabsContent value="graph" className="space-y-4">
          <SystemGraph />
        </TabsContent>
        
        <TabsContent value="test" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>React Flow Test</CardTitle>
              <CardDescription>Simple test to verify React Flow is working</CardDescription>
            </CardHeader>
            <CardContent>
              <TestGraph />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="resources" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <ResourceUsage />
            <Card>
              <CardHeader>
                <CardTitle>RAG System</CardTitle>
                <CardDescription>Retrieval Augmented Generation statistics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Documents</p>
                    <p className="text-2xl font-bold">1,247</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Index Size</p>
                    <p className="text-2xl font-bold">2.3GB</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Avg Query Time</p>
                    <p className="text-2xl font-bold">45ms</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Cache Hit Rate</p>
                    <p className="text-2xl font-bold">87%</p>
                  </div>
                </div>
                <div className="pt-4 border-t">
                  <div className="flex items-center justify-between text-sm">
                    <span>Embedding Model</span>
                    <Badge variant="secondary">text-embedding-3-small</Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm mt-2">
                    <span>Vector Database</span>
                    <Badge variant="secondary">sqlite-vec</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="logs" className="space-y-4">
          <SystemLogs />
        </TabsContent>
      </Tabs>
    </div>
  )
}

// Helper function
function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}