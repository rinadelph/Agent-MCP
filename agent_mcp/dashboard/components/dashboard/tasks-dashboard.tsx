"use client"

import React, { useState, useEffect } from "react"
import { 
  CheckSquare, Clock, AlertCircle, Users, Hash, Calendar, Tag,
  Search, Filter, Plus, MoreVertical, Eye, ChevronDown, Play, Pause,
  ArrowUp, ArrowDown, Minus, CheckCircle2, Target, Zap, GitBranch
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { apiClient, Task } from "@/lib/api"
import { useServerStore } from "@/lib/stores/server-store"
import { cn } from "@/lib/utils"

// Real data hook for tasks
const useTasksData = () => {
  const { activeServerId, servers } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!activeServerId || !activeServer || activeServer.status !== 'connected') {
      setLoading(false)
      setError(null)
      setTasks([])
      return
    }

    const fetchData = async () => {
      setLoading(true)
      try {
        const tasksData = await apiClient.getTasks()
        setTasks(tasksData)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch tasks')
        console.error('Error fetching tasks:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000) // Update every 5 seconds
    return () => clearInterval(interval)
  }, [activeServerId, activeServer])

  return { tasks, loading, error, isConnected: !!activeServerId && activeServer?.status === 'connected' }
}

const StatusDot = ({ status }: { status: Task['status'] }) => {
  const config = {
    in_progress: "bg-teal-400 shadow-teal-400/50 shadow-md animate-pulse",
    pending: "bg-amber-400 shadow-amber-400/50 shadow-md",
    completed: "bg-emerald-400 shadow-emerald-400/50 shadow-md",
    cancelled: "bg-slate-500 shadow-slate-500/50 shadow-md",
    failed: "bg-orange-400 shadow-orange-400/50 shadow-md animate-pulse",
  }
  
  return (
    <div className={cn(
      "w-2.5 h-2.5 rounded-full",
      config[status] || config.pending
    )} />
  )
}

const PriorityIcon = ({ priority }: { priority: Task['priority'] }) => {
  const config = {
    high: { icon: ArrowUp, className: "text-orange-400" },
    medium: { icon: Minus, className: "text-amber-400" },
    low: { icon: ArrowDown, className: "text-slate-400" },
  }
  
  const { icon: Icon, className } = config[priority]
  return <Icon className={cn("h-4 w-4", className)} />
}

const CompactTaskRow = ({ task }: { task: Task }) => {
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
          <StatusDot status={task.status} />
          <PriorityIcon priority={task.priority} />
          <div className="min-w-0 flex-1">
            <div className="font-medium text-sm text-white truncate">{task.title}</div>
            <div className="text-xs text-slate-500 font-mono">#{task.task_id.slice(-6)}</div>
          </div>
        </div>
      </TableCell>
      
      <TableCell className="py-3">
        <Badge 
          variant="outline" 
          className={cn(
            "text-xs font-semibold border-0 px-3 py-1.5 rounded-md",
            task.status === 'in_progress' && "bg-teal-500/15 text-teal-300 ring-1 ring-teal-500/20",
            task.status === 'pending' && "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/20",
            task.status === 'completed' && "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/20",
            task.status === 'cancelled' && "bg-slate-500/15 text-slate-300 ring-1 ring-slate-500/20",
            task.status === 'failed' && "bg-orange-500/15 text-orange-300 ring-1 ring-orange-500/20"
          )}
        >
          {task.status.replace('_', ' ').toUpperCase()}
        </Badge>
      </TableCell>
      
      <TableCell className="py-3 max-w-xs">
        <div className="text-sm text-slate-300 truncate">
          {task.description || "No description"}
        </div>
        {task.assigned_to && (
          <div className="text-xs text-slate-500 mt-1 flex items-center gap-1">
            <Users className="h-3 w-3" />
            {task.assigned_to}
          </div>
        )}
      </TableCell>
      
      <TableCell className="py-3">
        <Badge 
          variant="outline" 
          className={cn(
            "text-xs font-medium px-2 py-0.5",
            task.priority === 'high' && "bg-orange-500/10 text-orange-300 border-orange-500/20",
            task.priority === 'medium' && "bg-amber-500/10 text-amber-300 border-amber-500/20",
            task.priority === 'low' && "bg-slate-500/10 text-slate-300 border-slate-500/20"
          )}
        >
          {task.priority.toUpperCase()}
        </Badge>
      </TableCell>
      
      <TableCell className="py-3">
        <div className="flex flex-wrap gap-1">
          {task.parent_task && (
            <Badge variant="outline" className="text-xs px-2 py-0.5 bg-purple-500/10 text-purple-300 border-purple-500/20">
              <GitBranch className="h-3 w-3 mr-1" />
              Subtask
            </Badge>
          )}
          {task.child_tasks && task.child_tasks.length > 0 && (
            <Badge variant="outline" className="text-xs px-2 py-0.5 bg-blue-500/10 text-blue-300 border-blue-500/20">
              {task.child_tasks.length} children
            </Badge>
          )}
        </div>
      </TableCell>
      
      <TableCell className="py-3 text-xs text-slate-500 font-mono">
        {formatDate(task.updated_at)}
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
          {task.status === 'pending' && (
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-7 w-7 p-0 text-teal-400 hover:text-teal-300 hover:bg-teal-500/10"
            >
              <Play className="h-3.5 w-3.5" />
            </Button>
          )}
          {task.status === 'in_progress' && (
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-7 w-7 p-0 text-amber-400 hover:text-amber-300 hover:bg-amber-500/10"
            >
              <Pause className="h-3.5 w-3.5" />
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
        <div className="text-2xl font-bold text-white mb-1">{value}</div>
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

const CreateTaskModal = ({ onCreateTask }: { onCreateTask: (data: any) => void }) => {
  const [open, setOpen] = useState(false)
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium' as Task['priority'],
    assigned_to: ''
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title.trim()) return

    onCreateTask({
      title: formData.title.trim(),
      description: formData.description.trim() || undefined,
      priority: formData.priority,
      assigned_to: formData.assigned_to.trim() || undefined
    })

    setFormData({ title: '', description: '', priority: 'medium', assigned_to: '' })
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="bg-teal-600 hover:bg-teal-700 text-white shadow-lg hover:shadow-teal-500/25 transition-all duration-200">
          <Plus className="h-4 w-4 mr-1.5" />
          Create Task
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md bg-slate-900 border-slate-800 text-white">
        <DialogHeader>
          <DialogTitle className="text-lg">Create Task</DialogTitle>
          <DialogDescription className="text-slate-400">
            Define a new task for the system to execute.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider block mb-2">
              Task Title
            </label>
            <Input
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              placeholder="Analyze dataset and generate report"
              className="bg-slate-800 border-slate-700 text-white"
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider block mb-2">
              Description
            </label>
            <Textarea
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Detailed task requirements and objectives..."
              className="bg-slate-800 border-slate-700 text-white h-20 resize-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-400 uppercase tracking-wider block mb-2">
                Priority
              </label>
              <Select value={formData.priority} onValueChange={(value: Task['priority']) => setFormData(prev => ({ ...prev, priority: value }))}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-800">
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-400 uppercase tracking-wider block mb-2">
                Assign To
              </label>
              <Input
                value={formData.assigned_to}
                onChange={(e) => setFormData(prev => ({ ...prev, assigned_to: e.target.value }))}
                placeholder="agent-01"
                className="bg-slate-800 border-slate-700 text-white font-mono text-sm"
              />
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} size="sm">
              Cancel
            </Button>
            <Button type="submit" size="sm" className="bg-teal-600 hover:bg-teal-700 shadow-lg hover:shadow-teal-500/25 transition-all">
              Create Task
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function TasksDashboard() {
  const { tasks, loading, error, isConnected } = useTasksData()
  const { servers, activeServerId } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [priorityFilter, setPriorityFilter] = useState<string>('all')

  const filteredTasks = tasks.filter(task => {
    const matchesSearch = task.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (task.description && task.description.toLowerCase().includes(searchTerm.toLowerCase()))
    const matchesStatus = statusFilter === 'all' || task.status === statusFilter
    const matchesPriority = priorityFilter === 'all' || task.priority === priorityFilter
    return matchesSearch && matchesStatus && matchesPriority
  })

  const stats = {
    total: tasks.length,
    in_progress: tasks.filter(t => t.status === 'in_progress').length,
    pending: tasks.filter(t => t.status === 'pending').length,
    completed: tasks.filter(t => t.status === 'completed').length,
    failed: tasks.filter(t => t.status === 'failed').length,
  }

  const handleCreateTask = async (data: any) => {
    try {
      await apiClient.createTask(data)
    } catch (error) {
      console.error('Failed to create task:', error)
    }
  }

  if (!isConnected) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <CheckSquare className="h-12 w-12 text-slate-600 mx-auto" />
          <div>
            <h3 className="text-lg font-medium text-white mb-2">No Server Connection</h3>
            <p className="text-slate-400 text-sm">Connect to an MCP server to manage tasks</p>
          </div>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin h-8 w-8 border-2 border-teal-500 border-t-transparent rounded-full mx-auto" />
          <p className="text-slate-400 text-sm">Loading tasks...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <AlertCircle className="h-12 w-12 text-orange-500 mx-auto" />
          <div>
            <h3 className="text-lg font-medium text-white mb-2">Connection Error</h3>
            <p className="text-orange-400 text-sm">{error}</p>
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
          <h1 className="text-2xl font-bold text-white">Task Operations</h1>
          <p className="text-slate-400 text-sm">Orchestrate and monitor autonomous tasks</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="text-xs bg-teal-500/15 text-teal-300 border-teal-500/30 font-medium">
            <div className="w-2 h-2 bg-teal-400 rounded-full mr-2 animate-pulse" />
            {activeServer?.name}
          </Badge>
          <CreateTaskModal onCreateTask={handleCreateTask} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-4">
        <StatsCard 
          icon={Target} 
          label="Total" 
          value={stats.total} 
          change={stats.total > 0 ? `${stats.in_progress} active` : undefined}
          trend="neutral"
        />
        <StatsCard 
          icon={Zap} 
          label="Active" 
          value={stats.in_progress} 
          change={stats.total > 0 ? `${Math.round((stats.in_progress/stats.total)*100)}%` : "0%"}
          trend="up"
        />
        <StatsCard 
          icon={Clock} 
          label="Pending" 
          value={stats.pending} 
          change={stats.pending > 0 ? "Queued" : "None"}
          trend="neutral"
        />
        <StatsCard 
          icon={CheckCircle2} 
          label="Completed" 
          value={stats.completed} 
          change={stats.total > 0 ? `${Math.round((stats.completed/stats.total)*100)}% done` : "0%"}
          trend="up"
        />
        <StatsCard 
          icon={AlertCircle} 
          label="Failed" 
          value={stats.failed} 
          change={stats.failed > 0 ? "Need review" : "All good"}
          trend={stats.failed > 0 ? "down" : "neutral"}
        />
      </div>

      {/* Controls */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search tasks..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 bg-slate-900/60 border-slate-700/60 text-white placeholder:text-slate-400 focus:border-teal-500/50 focus:ring-teal-500/20 transition-all"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-36 bg-slate-900/60 border-slate-700/60 text-white">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-slate-900 border-slate-800">
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="in_progress">In Progress</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="cancelled">Cancelled</SelectItem>
          </SelectContent>
        </Select>
        <Select value={priorityFilter} onValueChange={setPriorityFilter}>
          <SelectTrigger className="w-32 bg-slate-900/60 border-slate-700/60 text-white">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-slate-900 border-slate-800">
            <SelectItem value="all">All Priority</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Tasks Table */}
      <div className="bg-slate-900/30 border border-slate-800/50 rounded-lg overflow-hidden backdrop-blur-sm">
        <Table>
          <TableHeader>
            <TableRow className="border-slate-800/50 hover:bg-transparent">
              <TableHead className="text-slate-400 font-medium text-xs uppercase tracking-wider">Task</TableHead>
              <TableHead className="text-slate-400 font-medium text-xs uppercase tracking-wider">Status</TableHead>
              <TableHead className="text-slate-400 font-medium text-xs uppercase tracking-wider">Details</TableHead>
              <TableHead className="text-slate-400 font-medium text-xs uppercase tracking-wider">Priority</TableHead>
              <TableHead className="text-slate-400 font-medium text-xs uppercase tracking-wider">Relations</TableHead>
              <TableHead className="text-slate-400 font-medium text-xs uppercase tracking-wider">Updated</TableHead>
              <TableHead className="text-slate-400 font-medium text-xs uppercase tracking-wider w-24">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredTasks.map((task) => (
              <CompactTaskRow
                key={task.task_id}
                task={task}
              />
            ))}
          </TableBody>
        </Table>
        
        {filteredTasks.length === 0 && (
          <div className="p-12 text-center">
            <CheckSquare className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No tasks found</h3>
            <p className="text-slate-400 text-sm mb-4">
              {tasks.length === 0 ? "Create your first task to get started" : "No tasks match your current filters"}
            </p>
            {tasks.length === 0 && <CreateTaskModal onCreateTask={handleCreateTask} />}
          </div>
        )}
      </div>
    </div>
  )
}