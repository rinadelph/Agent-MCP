"use client"

import React, { useState, useEffect } from "react"
import { 
  User, Users, Activity, Zap, Power, PowerOff, Clock, Hash, Settings, Trash2, Play, 
  StopCircle, AlertCircle, CheckCircle2, Shield, Cpu, Database, Network, Terminal,
  Search, Filter, Plus, MoreVertical, Eye, GitBranch, Layers, Workflow, Grid, List
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

// Real data hook for agents
const useAgentsData = () => {
  const { activeServerId, servers } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!activeServerId || !activeServer || activeServer.status !== 'connected') {
      setLoading(false)
      setError(null)
      setAgents([])
      return
    }

    const fetchData = async () => {
      setLoading(true)
      try {
        const agentsData = await apiClient.getAgents()
        setAgents(agentsData)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch agents')
        console.error('Error fetching agents:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000) // Update every 5 seconds
    return () => clearInterval(interval)
  }, [activeServerId, activeServer])

  return { agents, loading, error, isConnected: !!activeServerId && activeServer?.status === 'connected' }
}

const StatusDot = ({ status }: { status: Agent['status'] }) => {
  const config = {
    running: "bg-teal-400 shadow-teal-400/50 shadow-md",
    pending: "bg-amber-400 shadow-amber-400/50 shadow-md animate-pulse",
    terminated: "bg-slate-500 shadow-slate-500/50 shadow-md",
    failed: "bg-orange-400 shadow-orange-400/50 shadow-md animate-pulse",
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
  return <Icon className="h-4 w-4 text-slate-400" />
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
    <TableRow className="border-slate-800/50 hover:bg-slate-900/30 group transition-colors">
      <TableCell className="py-3">
        <div className="flex items-center gap-3">
          <StatusDot status={agent.status} />
          <AgentTypeIcon agentId={agent.agent_id} />
          <div className="min-w-0 flex-1">
            <div className="font-medium text-sm text-white dark:text-white text-slate-900 truncate">{agent.agent_id}</div>
            <div className="text-xs text-slate-500 dark:text-slate-500 text-slate-600 font-mono">#{agent.agent_id.slice(-6)}</div>
          </div>
        </div>
      </TableCell>
      
      <TableCell className="py-3">
        <Badge 
          variant="outline" 
          className={cn(
            "text-xs font-semibold border-0 px-3 py-1.5 rounded-md",
            agent.status === 'running' && "bg-teal-500/15 text-teal-300 ring-1 ring-teal-500/20",
            agent.status === 'pending' && "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/20",
            agent.status === 'terminated' && "bg-slate-500/15 text-slate-300 ring-1 ring-slate-500/20",
            agent.status === 'failed' && "bg-orange-500/15 text-orange-300 ring-1 ring-orange-500/20"
          )}
        >
          {agent.status.toUpperCase()}
        </Badge>
      </TableCell>
      
      <TableCell className="py-3 max-w-xs">
        <div className="text-sm text-slate-300 dark:text-slate-300 text-slate-700 truncate">
          {agent.current_task || "No active task"}
        </div>
        {agent.current_task && (
          <div className="text-xs text-slate-500 dark:text-slate-500 text-slate-600 mt-1 truncate">
            {agent.working_directory || "No directory set"}
          </div>
        )}
      </TableCell>
      
      <TableCell className="py-3">
        <div className="flex flex-wrap gap-1">
          {agent.capabilities?.slice(0, 2).map((cap, i) => (
            <Badge key={i} variant="outline" className="text-xs px-2 py-0.5 bg-purple-500/10 text-purple-300 border-purple-500/20 font-medium">
              {cap}
            </Badge>
          ))}
          {agent.capabilities && agent.capabilities.length > 2 && (
            <Badge variant="outline" className="text-xs px-2 py-0.5 bg-slate-600/10 text-slate-400 border-slate-600/20 font-medium">
              +{agent.capabilities.length - 2}
            </Badge>
          )}
        </div>
      </TableCell>
      
      <TableCell className="py-3 text-xs text-slate-500 dark:text-slate-500 text-slate-600 font-mono">
        {formatDate(agent.updated_at)}
      </TableCell>
      
      <TableCell className="py-3">
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-7 w-7 p-0 text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <Eye className="h-3.5 w-3.5" />
          </Button>
          {agent.status === 'running' && (
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => onTerminate(agent.agent_id)}
              className="h-7 w-7 p-0 text-red-400 hover:text-red-300 hover:bg-red-500/10"
            >
              <PowerOff className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-7 w-7 p-0 text-slate-400 hover:text-white hover:bg-slate-800"
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
  <div className="bg-slate-900/60 border border-slate-800/60 rounded-xl p-5 backdrop-blur-sm hover:bg-slate-900/80 transition-all duration-200 group">
    <div className="flex items-center justify-between">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Icon className="h-4 w-4 text-slate-400 group-hover:text-slate-300 transition-colors" />
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</span>
        </div>
        <div className="text-2xl font-bold text-white dark:text-white text-slate-900 mb-1">{value}</div>
        {change && (
          <div className={cn(
            "text-xs font-medium",
            trend === 'up' && "text-teal-400",
            trend === 'down' && "text-orange-400",
            trend === 'neutral' && "text-slate-400"
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
        <Button size="sm" className="bg-teal-600 hover:bg-teal-700 text-white shadow-lg hover:shadow-teal-500/25 transition-all duration-200">
          <Plus className="h-4 w-4 mr-1.5" />
          Deploy
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md bg-slate-900 border-slate-800 text-white">
        <DialogHeader>
          <DialogTitle className="text-lg">Deploy Agent</DialogTitle>
          <DialogDescription className="text-slate-400">
            Configure a new agent for deployment.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider block mb-2">
              Agent ID
            </label>
            <Input
              value={formData.agent_id}
              onChange={(e) => setFormData(prev => ({ ...prev, agent_id: e.target.value }))}
              placeholder="worker-analytics-01"
              className="bg-slate-800 border-slate-700 text-white"
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider block mb-2">
              Capabilities
            </label>
            <Textarea
              value={formData.capabilities}
              onChange={(e) => setFormData(prev => ({ ...prev, capabilities: e.target.value }))}
              placeholder="data-analysis, file-ops, web-search"
              className="bg-slate-800 border-slate-700 text-white h-20 resize-none"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider block mb-2">
              Working Directory
            </label>
            <Input
              value={formData.working_directory}
              onChange={(e) => setFormData(prev => ({ ...prev, working_directory: e.target.value }))}
              placeholder="/workspace/analytics"
              className="bg-slate-800 border-slate-700 text-white font-mono text-sm"
            />
          </div>
          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} size="sm">
              Cancel
            </Button>
            <Button type="submit" size="sm" className="bg-teal-600 hover:bg-teal-700 shadow-lg hover:shadow-teal-500/25 transition-all">
              Deploy
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function AgentsDashboard() {
  const { agents, loading, error, isConnected } = useAgentsData()
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
          <Network className="h-12 w-12 text-slate-600 mx-auto" />
          <div>
            <h3 className="text-lg font-medium text-white mb-2">No Server Connection</h3>
            <p className="text-slate-400 text-sm">Connect to an MCP server to manage agents</p>
          </div>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto" />
          <p className="text-slate-400 text-sm">Loading agents...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto" />
          <div>
            <h3 className="text-lg font-medium text-white mb-2">Connection Error</h3>
            <p className="text-red-400 text-sm">{error}</p>
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
          <h1 className="text-2xl font-bold text-white dark:text-white text-slate-900">Agent Fleet</h1>
          <p className="text-slate-400 dark:text-slate-400 text-slate-600 text-sm">Monitor and manage autonomous agents</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="text-xs bg-teal-500/15 text-teal-300 border-teal-500/30 font-medium">
            <div className="w-2 h-2 bg-teal-400 rounded-full mr-2 animate-pulse" />
            {activeServer?.name}
          </Badge>
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
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search agents..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 bg-slate-900/60 border-slate-700/60 text-white placeholder:text-slate-400 focus:border-teal-500/50 focus:ring-teal-500/20 transition-all"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-32 bg-slate-900/50 border-slate-800 text-white">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-slate-900 border-slate-800">
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="terminated">Terminated</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Agents Table */}
      <div className="bg-slate-900/30 border border-slate-800/50 rounded-lg overflow-hidden backdrop-blur-sm">
        <Table>
          <TableHeader>
            <TableRow className="border-slate-800/50 hover:bg-transparent">
              <TableHead className="text-slate-400 dark:text-slate-400 text-slate-600 font-medium text-xs uppercase tracking-wider">Agent</TableHead>
              <TableHead className="text-slate-400 dark:text-slate-400 text-slate-600 font-medium text-xs uppercase tracking-wider">Status</TableHead>
              <TableHead className="text-slate-400 dark:text-slate-400 text-slate-600 font-medium text-xs uppercase tracking-wider">Current Task</TableHead>
              <TableHead className="text-slate-400 dark:text-slate-400 text-slate-600 font-medium text-xs uppercase tracking-wider">Capabilities</TableHead>
              <TableHead className="text-slate-400 dark:text-slate-400 text-slate-600 font-medium text-xs uppercase tracking-wider">Updated</TableHead>
              <TableHead className="text-slate-400 dark:text-slate-400 text-slate-600 font-medium text-xs uppercase tracking-wider w-24">Actions</TableHead>
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
            <Users className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white dark:text-white text-slate-900 mb-2">No agents found</h3>
            <p className="text-slate-400 dark:text-slate-400 text-slate-600 text-sm mb-4">
              {agents.length === 0 ? "Deploy your first agent to get started" : "No agents match your current filters"}
            </p>
            {agents.length === 0 && <CreateAgentModal onCreateAgent={handleCreateAgent} />}
          </div>
        )}
      </div>
    </div>
  )
}