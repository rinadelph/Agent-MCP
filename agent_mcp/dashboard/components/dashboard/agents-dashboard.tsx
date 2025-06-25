"use client"

import React, { useState, useEffect, useCallback, useMemo } from "react"
import { 
  User, Users, Activity, Zap, Power, PowerOff, Clock, Hash, Settings, Trash2, Play, 
  StopCircle, AlertCircle, CheckCircle2, Shield, Cpu, Database, Network, Terminal,
  Search, Filter, Plus, MoreVertical, Eye, GitBranch, Layers, Workflow, Grid, List, RefreshCw
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { apiClient, Agent } from "@/lib/api"
import { useServerStore } from "@/lib/stores/server-store"
import { cn } from "@/lib/utils"

// Cache for agents data
const agentsCache = new Map<string, { data: Agent[], timestamp: number }>()
const CACHE_DURATION = 30000 // 30 seconds
const REFRESH_INTERVAL = 60000 // 1 minute for background refresh

// Real data hook for agents with caching
const useAgentsData = () => {
  const { activeServerId, servers } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastFetch, setLastFetch] = useState<number>(0)

  const fetchData = useCallback(async (forceRefresh = false) => {
    if (!activeServerId || !activeServer || activeServer.status !== 'connected') {
      setAgents([])
      setError(null)
      setLoading(false)
      return
    }

    const cacheKey = `${activeServerId}-agents`
    const now = Date.now()
    const cached = agentsCache.get(cacheKey)

    // Use cache if it's fresh and not forcing refresh
    if (!forceRefresh && cached && (now - cached.timestamp) < CACHE_DURATION) {
      setAgents(cached.data)
      setError(null)
      setLoading(false)
      return
    }

    // Only show loading on first fetch or force refresh
    if (agents.length === 0 || forceRefresh) {
      setLoading(true)
    }

    try {
      const agentsData = await apiClient.getAgents()
      
      // Update cache
      agentsCache.set(cacheKey, { data: agentsData, timestamp: now })
      
      setAgents(agentsData)
      setError(null)
      setLastFetch(now)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch agents')
      console.error('Error fetching agents:', err)
    } finally {
      setLoading(false)
    }
  }, [activeServerId, activeServer, agents.length])

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
    agents, 
    loading, 
    error, 
    refresh,
    lastFetch,
    isConnected: !!activeServerId && activeServer?.status === 'connected' 
  }), [agents, loading, error, refresh, lastFetch, activeServerId, activeServer])
}

const StatusDot = ({ status }: { status: Agent['status'] }) => {
  const config = {
    running: "bg-primary shadow-primary/50 shadow-md",
    pending: "bg-warning shadow-warning/50 shadow-md animate-pulse",
    terminated: "bg-muted-foreground shadow-muted-foreground/50 shadow-md",
    failed: "bg-destructive shadow-destructive/50 shadow-md animate-pulse",
  }
  
  return (
    <div className={cn(
      "w-2.5 h-2.5 rounded-full",
      config[status] || config.pending
    )} />
  )
}

const AgentTypeIcon = ({ agentId }: { agentId: string }) => {
  const getIcon = () => {
    if (agentId.includes('admin')) return Shield
    if (agentId.includes('worker')) return Cpu
    if (agentId.includes('analysis')) return Database
    if (agentId.includes('security')) return Shield
    return Terminal
  }
  
  const Icon = getIcon()
  return <Icon className="h-4 w-4 text-muted-foreground" />
}

const CompactAgentRow = ({ agent, onTerminate }: { agent: Agent, onTerminate: (id: string) => void }) => {
  const [mounted, setMounted] = useState(false)
  
  useEffect(() => {
    setMounted(true)
  }, [])

  const formatDate = (dateString: string) => {
    if (!mounted) return "..."
    return new Date(dateString).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <TableRow className="border-border/50 hover:bg-muted/30 group transition-colors">
      <TableCell className="py-3">
        <div className="flex items-center gap-3">
          <StatusDot status={agent.status} />
          <AgentTypeIcon agentId={agent.agent_id} />
          <div className="min-w-0 flex-1">
            <div className="font-medium text-sm text-foreground truncate">{agent.agent_id}</div>
            <div className="text-xs text-muted-foreground font-mono">#{agent.agent_id.slice(-6)}</div>
          </div>
        </div>
      </TableCell>
      
      <TableCell className="py-3">
        <Badge 
          variant="outline" 
          className={cn(
            "text-xs font-semibold border-0 px-3 py-1.5 rounded-md",
            agent.status === 'running' && "bg-primary/15 text-primary ring-1 ring-primary/20",
            agent.status === 'pending' && "bg-warning/15 text-warning ring-1 ring-warning/20",
            agent.status === 'terminated' && "bg-muted/50 text-muted-foreground ring-1 ring-border",
            agent.status === 'failed' && "bg-destructive/15 text-destructive ring-1 ring-destructive/20"
          )}
        >
          {agent.status.toUpperCase()}
        </Badge>
      </TableCell>
      
      <TableCell className="py-3 max-w-xs">
        <div className="text-sm text-foreground truncate">
          {agent.current_task || "No active task"}
        </div>
        {agent.current_task && (
          <div className="text-xs text-muted-foreground mt-1 truncate">
            {agent.working_directory || "No directory set"}
          </div>
        )}
      </TableCell>
      
      <TableCell className="py-3">
        <div className="flex flex-wrap gap-1">
          {agent.capabilities?.slice(0, 2).map((cap, i) => (
            <Badge key={i} variant="outline" className="text-xs px-2 py-0.5 bg-accent/10 text-accent-foreground border-accent/20 font-medium">
              {cap}
            </Badge>
          ))}
          {agent.capabilities && agent.capabilities.length > 2 && (
            <Badge variant="outline" className="text-xs px-2 py-0.5 bg-muted/50 text-muted-foreground border-border font-medium">
              +{agent.capabilities.length - 2}
            </Badge>
          )}
        </div>
      </TableCell>
      
      <TableCell className="py-3 text-xs text-muted-foreground font-mono">
        {formatDate(agent.updated_at)}
      </TableCell>
      
      <TableCell className="py-3">
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground hover:bg-muted"
          >
            <Eye className="h-3.5 w-3.5" />
          </Button>
          {agent.status === 'running' && (
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => onTerminate(agent.agent_id)}
              className="h-7 w-7 p-0 text-destructive hover:text-destructive/80 hover:bg-destructive/10"
            >
              <PowerOff className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground hover:bg-muted"
          >
            <MoreVertical className="h-3.5 w-3.5" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  )
}

const StatsCard = ({ icon: Icon, label, value, change, trend }: {
  icon: any
  label: string
  value: number
  change?: string
  trend?: 'up' | 'down' | 'neutral'
}) => (
  <div className="bg-card/80 border border-border/60 rounded-xl p-5 backdrop-blur-sm hover:bg-card transition-all duration-200 group">
    <div className="flex items-center justify-between">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Icon className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{label}</span>
        </div>
        <div className="text-2xl font-bold text-foreground mb-1">{value}</div>
        {change && (
          <div className={cn(
            "text-xs font-medium",
            trend === 'up' && "text-primary",
            trend === 'down' && "text-destructive",
            trend === 'neutral' && "text-muted-foreground"
          )}>
            {change}
          </div>
        )}
      </div>
    </div>
  </div>
)

const CreateAgentModal = ({ onCreateAgent }: { onCreateAgent: (data: any) => void }) => {
  const [open, setOpen] = useState(false)
  const [formData, setFormData] = useState({
    agent_id: '',
    capabilities: '',
    working_directory: ''
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.agent_id.trim()) return

    const capabilities = formData.capabilities
      .split(',')
      .map(c => c.trim())
      .filter(c => c.length > 0)

    onCreateAgent({
      agent_id: formData.agent_id.trim(),
      capabilities: capabilities.length > 0 ? capabilities : undefined,
      working_directory: formData.working_directory.trim() || undefined
    })

    setFormData({ agent_id: '', capabilities: '', working_directory: '' })
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg hover:shadow-primary/25 transition-all duration-200">
          <Plus className="h-4 w-4 mr-1.5" />
          Deploy
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md bg-card border-border text-card-foreground">
        <DialogHeader>
          <DialogTitle className="text-lg">Deploy Agent</DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Configure a new agent for deployment.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider block mb-2">
              Agent ID
            </label>
            <Input
              value={formData.agent_id}
              onChange={(e) => setFormData(prev => ({ ...prev, agent_id: e.target.value }))}
              placeholder="worker-analytics-01"
              className="bg-background border-border text-foreground"
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider block mb-2">
              Capabilities
            </label>
            <Textarea
              value={formData.capabilities}
              onChange={(e) => setFormData(prev => ({ ...prev, capabilities: e.target.value }))}
              placeholder="data-analysis, file-ops, web-search"
              className="bg-background border-border text-foreground h-20 resize-none"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider block mb-2">
              Working Directory
            </label>
            <Input
              value={formData.working_directory}
              onChange={(e) => setFormData(prev => ({ ...prev, working_directory: e.target.value }))}
              placeholder="/workspace/analytics"
              className="bg-background border-border text-foreground font-mono text-sm"
            />
          </div>
          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} size="sm">
              Cancel
            </Button>
            <Button type="submit" size="sm" className="bg-primary hover:bg-primary/90 shadow-lg hover:shadow-primary/25 transition-all">
              Deploy
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function AgentsDashboard() {
  const { agents, loading, error, refresh, lastFetch, isConnected } = useAgentsData()
  const { servers, activeServerId } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const filteredAgents = agents.filter(agent => {
    const matchesSearch = agent.agent_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (agent.current_task && agent.current_task.toLowerCase().includes(searchTerm.toLowerCase()))
    const matchesStatus = statusFilter === 'all' || agent.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const stats = {
    total: agents.length,
    running: agents.filter(a => a.status === 'running').length,
    pending: agents.filter(a => a.status === 'pending').length,
    failed: agents.filter(a => a.status === 'failed').length,
  }

  const handleCreateAgent = async (data: any) => {
    try {
      await apiClient.createAgent(data)
    } catch (error) {
      console.error('Failed to create agent:', error)
    }
  }

  const handleTerminateAgent = async (agentId: string) => {
    try {
      await apiClient.terminateAgent(agentId)
    } catch (error) {
      console.error('Failed to terminate agent:', error)
    }
  }

  if (!isConnected) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <Network className="h-12 w-12 text-muted-foreground mx-auto" />
          <div>
            <h3 className="text-lg font-medium text-foreground mb-2">No Server Connection</h3>
            <p className="text-muted-foreground text-sm">Connect to an MCP server to manage agents</p>
          </div>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full mx-auto" />
          <p className="text-muted-foreground text-sm">Loading agents...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto" />
          <div>
            <h3 className="text-lg font-medium text-foreground mb-2">Connection Error</h3>
            <p className="text-destructive text-sm">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Agent Fleet</h1>
          <p className="text-muted-foreground text-sm">Monitor and manage autonomous agents</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="text-xs bg-primary/15 text-primary border-primary/30 font-medium">
            <div className="w-2 h-2 bg-primary rounded-full mr-2 animate-pulse" />
            {activeServer?.name}
          </Badge>
          {lastFetch > 0 && (
            <span className="text-xs text-muted-foreground">
              Last updated: {new Date(lastFetch).toLocaleTimeString()}
            </span>
          )}
          <Button 
            variant="outline" 
            size="sm" 
            onClick={refresh}
            disabled={loading}
            className="text-xs"
          >
            <RefreshCw className={cn("h-3.5 w-3.5 mr-1.5", loading && "animate-spin")} />
            Refresh
          </Button>
          <CreateAgentModal onCreateAgent={handleCreateAgent} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatsCard 
          icon={Users} 
          label="Total" 
          value={stats.total} 
          change={stats.total > 0 ? `${stats.running} active` : undefined}
          trend="neutral"
        />
        <StatsCard 
          icon={CheckCircle2} 
          label="Running" 
          value={stats.running} 
          change={stats.total > 0 ? `${Math.round((stats.running/stats.total)*100)}%` : "0%"}
          trend="up"
        />
        <StatsCard 
          icon={Clock} 
          label="Pending" 
          value={stats.pending} 
          change={stats.pending > 0 ? "Waiting" : "None"}
          trend="neutral"
        />
        <StatsCard 
          icon={AlertCircle} 
          label="Failed" 
          value={stats.failed} 
          change={stats.failed > 0 ? "Need attention" : "All good"}
          trend={stats.failed > 0 ? "down" : "neutral"}
        />
      </div>

      {/* Controls */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search agents..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 bg-background border-border text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:ring-primary/20 transition-all"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-32 bg-background border-border text-foreground">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-background border-border">
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="terminated">Terminated</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Agents Table */}
      <div className="bg-card/30 border border-border/50 rounded-lg overflow-hidden backdrop-blur-sm">
        <Table>
          <TableHeader>
            <TableRow className="border-border/50 hover:bg-transparent">
              <TableHead className="text-muted-foreground font-medium text-xs uppercase tracking-wider">Agent</TableHead>
              <TableHead className="text-muted-foreground font-medium text-xs uppercase tracking-wider">Status</TableHead>
              <TableHead className="text-muted-foreground font-medium text-xs uppercase tracking-wider">Current Task</TableHead>
              <TableHead className="text-muted-foreground font-medium text-xs uppercase tracking-wider">Capabilities</TableHead>
              <TableHead className="text-muted-foreground font-medium text-xs uppercase tracking-wider">Updated</TableHead>
              <TableHead className="text-muted-foreground font-medium text-xs uppercase tracking-wider w-24">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredAgents.map((agent) => (
              <CompactAgentRow
                key={agent.agent_id}
                agent={agent}
                onTerminate={handleTerminateAgent}
              />
            ))}
          </TableBody>
        </Table>
        
        {filteredAgents.length === 0 && (
          <div className="p-12 text-center">
            <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">No agents found</h3>
            <p className="text-muted-foreground text-sm mb-4">
              {agents.length === 0 ? "Deploy your first agent to get started" : "No agents match your current filters"}
            </p>
            {agents.length === 0 && <CreateAgentModal onCreateAgent={handleCreateAgent} />}
          </div>
        )}
      </div>
    </div>
  )
}