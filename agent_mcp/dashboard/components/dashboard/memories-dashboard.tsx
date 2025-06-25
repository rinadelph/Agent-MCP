"use client"

import React, { useState, useEffect } from 'react'
import { 
  Brain, 
  Search, 
  Plus, 
  MoreVertical, 
  Edit, 
  Trash2, 
  Eye,
  Copy,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  Database,
  Network
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { useDataStore } from '@/lib/stores/data-store'
import { useServerStore } from '@/lib/stores/server-store'
import { apiClient, type Memory } from '@/lib/api'
import { CreateMemoryModal } from './modals/create-memory-modal'
import { ViewMemoryModal } from './modals/view-memory-modal'
import { SmartValueEditor } from './modals/smart-value-editor'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'

// Stats card component
const StatsCard = ({ icon: Icon, label, value, change, trend }: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: number
  change?: string
  trend?: 'up' | 'down' | 'neutral'
}) => (
  <div className="bg-card/80 border border-border/60 rounded-xl p-[var(--space-fluid-md)] backdrop-blur-sm hover:bg-card transition-all duration-200 group">
    <div className="flex items-center justify-between">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Icon className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
          <span className="text-fluid-xs font-semibold text-muted-foreground uppercase tracking-wider">{label}</span>
        </div>
        <div className="text-fluid-2xl font-bold text-foreground mb-1">{value}</div>
        {change && (
          <div className={cn(
            "text-fluid-xs font-medium",
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

// Memory row component
const MemoryRow = ({ memory, onView, onEdit, onDelete }: {
  memory: Memory
  onView: (memory: Memory) => void
  onEdit: (memory: Memory) => void
  onDelete: (memory: Memory) => void
}) => {
  const metadata = memory._metadata

  const formatValue = (value: any) => {
    if (typeof value === 'string') {
      return value.length > 30 ? value.substring(0, 30) + '...' : value
    }
    return JSON.stringify(value).length > 30 
      ? JSON.stringify(value).substring(0, 30) + '...'
      : JSON.stringify(value)
  }

  const formatKey = (key: string) => {
    return key.length > 25 ? key.substring(0, 25) + '...' : key
  }

  return (
    <TableRow className="border-border/50 hover:bg-muted/30 group transition-all duration-200">
      {/* Memory Key - More compact */}
      <TableCell className="py-2 px-2 sm:px-4">
        <div className="flex items-center gap-2">
          <Brain className="h-3 w-3 text-primary flex-shrink-0" />
          <div className="min-w-0 flex-1">
            <div className="font-medium text-xs sm:text-sm text-foreground truncate" title={memory.context_key}>
              {formatKey(memory.context_key)}
            </div>
            {memory.description && (
              <div className="text-xs text-muted-foreground truncate hidden sm:block" title={memory.description}>
                {memory.description.length > 20 ? memory.description.substring(0, 20) + '...' : memory.description}
              </div>
            )}
          </div>
        </div>
      </TableCell>
      
      {/* Value - Hidden on mobile, shown on tablet+ */}
      <TableCell className="py-2 px-2 hidden md:table-cell">
        <div className="font-mono text-xs text-foreground truncate max-w-[150px]" title={JSON.stringify(memory.value)}>
          {formatValue(memory.value)}
        </div>
      </TableCell>
      
      {/* Status - Compact badges */}
      <TableCell className="py-2 px-2 hidden lg:table-cell">
        <div className="flex items-center gap-1 flex-wrap">
          {metadata?.size_kb && metadata.size_kb > 1 && (
            <Badge variant="outline" className="text-xs px-1 py-0">
              {metadata.size_kb}KB
            </Badge>
          )}
          {metadata?.is_stale && (
            <Badge variant="outline" className="text-xs px-1 py-0 bg-orange-500/15 text-orange-600 border-orange-500/30">
              Stale
            </Badge>
          )}
          {metadata?.is_large && (
            <Badge variant="outline" className="text-xs px-1 py-0 bg-red-500/15 text-red-600 border-red-500/30">
              Large
            </Badge>
          )}
        </div>
      </TableCell>
      
      {/* Updated info - Compact */}
      <TableCell className="py-2 px-2 hidden sm:table-cell">
        <div className="text-xs text-muted-foreground">
          <div className="truncate">{memory.updated_by}</div>
          <div>{memory.last_updated ? new Date(memory.last_updated).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : 'Unknown'}</div>
        </div>
      </TableCell>
      
      {/* Actions - Always visible, compact */}
      <TableCell className="py-2 px-1">
        <div className="flex items-center gap-0.5 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => onView(memory)}
            className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground hover:bg-muted"
            title="View details"
          >
            <Eye className="h-3 w-3" />
          </Button>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => onEdit(memory)}
            className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground hover:bg-muted"
            title="Edit memory"
          >
            <Edit className="h-3 w-3" />
          </Button>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => onDelete(memory)}
            className="h-6 w-6 p-0 text-destructive hover:text-destructive/80 hover:bg-destructive/10"
            title="Delete memory"
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  )
}

// Edit Memory Modal Component
const EditMemoryModal = ({ memory, open, onOpenChange, onUpdateMemory }: {
  memory: Memory
  open: boolean
  onOpenChange: (open: boolean) => void
  onUpdateMemory: (data: { context_key: string; context_value: any; description?: string }) => Promise<void>
}) => {
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    context_key: memory.context_key,
    context_value: memory.value,
    description: memory.description || ''
  })

  React.useEffect(() => {
    if (open && memory) {
      setFormData({
        context_key: memory.context_key,
        context_value: memory.value,
        description: memory.description || ''
      })
    }
  }, [open, memory])

  const handleValueChange = (value: any) => {
    setFormData(prev => ({ ...prev, context_value: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    setLoading(true)
    try {
      await onUpdateMemory({
        context_key: formData.context_key,
        context_value: formData.context_value,
        description: formData.description.trim() || undefined
      })
    } catch (error) {
      console.error('Failed to update memory:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg bg-card border-border text-card-foreground max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-lg">Edit Memory</DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Update the memory entry. The key cannot be changed.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Context Key (Read-only) */}
          <div className="space-y-2">
            <Label htmlFor="context_key" className="text-sm font-medium text-foreground">
              Memory Key (Read-only)
            </Label>
            <Input
              id="context_key"
              value={formData.context_key}
              disabled
              className="bg-muted/50 border-border text-muted-foreground font-mono text-sm"
            />
          </div>

          {/* Context Value */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              Memory Value
            </Label>
            <SmartValueEditor
              value={formData.context_value}
              onChange={handleValueChange}
              className="border rounded-lg p-3 bg-background"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description" className="text-sm font-medium text-foreground">
              Description (Optional)
            </Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Brief description of what this memory stores..."
              className="bg-background border-border text-foreground h-20 resize-none"
              rows={3}
            />
          </div>

          <DialogFooter className="gap-2 pt-4">
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => onOpenChange(false)} 
              size="sm"
              disabled={loading}
            >
              Cancel
            </Button>
            <Button 
              type="submit" 
              size="sm" 
              disabled={loading}
              className="bg-primary hover:bg-primary/90 shadow-lg hover:shadow-primary/25 transition-all"
            >
              {loading ? (
                <>
                  <div className="h-3 w-3 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" />
                  Updating...
                </>
              ) : (
                <>
                  <Edit className="h-3 w-3 mr-2" />
                  Update Memory
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function MemoriesDashboard() {
  const { servers, activeServerId } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  const { data, loading, error, refreshData, getAdminToken } = useDataStore()
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<string>('last_updated')
  
  // Modal state management
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null)
  const [viewModalOpen, setViewModalOpen] = useState(false)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [isOperationLoading, setIsOperationLoading] = useState(false)
  const [operationError, setOperationError] = useState<string | null>(null)
  
  const isConnected = !!activeServerId && activeServer?.status === 'connected'

  // Convert context data to memories format
  const memories: Memory[] = React.useMemo(() => {
    console.log('🔍 Debug - Raw data:', data)
    console.log('🔍 Debug - Context data:', data?.context)
    console.log('🔍 Debug - Context length:', data?.context?.length)
    
    if (!data?.context) {
      console.log('❌ No context data found')
      return []
    }
    
    console.log('✅ Converting context to memories, count:', data.context.length)
    return data.context.map(ctx => ({
      context_key: ctx.context_key,
      value: ctx.value,
      description: ctx.description,
      last_updated: ctx.last_updated,
      updated_by: ctx.updated_by,
      _metadata: {
        size_bytes: JSON.stringify(ctx.value).length,
        size_kb: Math.round(JSON.stringify(ctx.value).length / 1024 * 100) / 100,
        json_valid: true,
        days_old: ctx.last_updated ? Math.floor((Date.now() - new Date(ctx.last_updated).getTime()) / (1000 * 60 * 60 * 24)) : undefined,
        is_stale: ctx.last_updated ? (Date.now() - new Date(ctx.last_updated).getTime()) > (30 * 24 * 60 * 60 * 1000) : false,
        is_large: JSON.stringify(ctx.value).length > 10240
      }
    }))
  }, [data?.context])

  // Fetch data on mount and when server changes
  useEffect(() => {
    if (activeServerId && activeServer?.status === 'connected') {
      refreshData()
    }
  }, [activeServerId, activeServer?.status, refreshData])

  // Filter and sort memories
  const filteredMemories = React.useMemo(() => {
    let filtered = memories.filter(memory => 
      memory.context_key.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (memory.description && memory.description.toLowerCase().includes(searchTerm.toLowerCase())) ||
      JSON.stringify(memory.value).toLowerCase().includes(searchTerm.toLowerCase())
    )

    // Sort memories
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'key':
          return a.context_key.localeCompare(b.context_key)
        case 'size':
          return (b._metadata?.size_bytes || 0) - (a._metadata?.size_bytes || 0)
        case 'last_updated':
        default:
          return new Date(b.last_updated).getTime() - new Date(a.last_updated).getTime()
      }
    })

    return filtered
  }, [memories, searchTerm, sortBy])

  // Calculate stats
  const stats = React.useMemo(() => {
    const total = memories.length
    const stale = memories.filter(m => m._metadata?.is_stale).length
    const large = memories.filter(m => m._metadata?.is_large).length
    const errors = memories.filter(m => !m._metadata?.json_valid).length
    
    return {
      total,
      stale,
      large,
      errors
    }
  }, [memories])

  const handleView = (memory: Memory) => {
    setSelectedMemory(memory)
    setViewModalOpen(true)
  }

  const handleEdit = (memory: Memory) => {
    setSelectedMemory(memory)
    setEditModalOpen(true)
  }

  const handleDelete = async (memory: Memory) => {
    if (!window.confirm(`Are you sure you want to delete the memory "${memory.context_key}"? This action cannot be undone.`)) {
      return
    }

    const adminToken = getAdminToken()
    if (!adminToken) {
      setOperationError('No admin token available for delete operation')
      return
    }

    setIsOperationLoading(true)
    setOperationError(null)

    try {
      await apiClient.deleteMemory(memory.context_key, adminToken)
      await refreshData() // Refresh data after successful delete
      console.log('Memory deleted successfully:', memory.context_key)
    } catch (error) {
      console.error('Failed to delete memory:', error)
      setOperationError(error instanceof Error ? error.message : 'Failed to delete memory')
    } finally {
      setIsOperationLoading(false)
    }
  }

  const handleCreateMemory = async (data: {
    context_key: string
    context_value: any
    description?: string
  }) => {
    const adminToken = getAdminToken()
    if (!adminToken) {
      throw new Error('No admin token available for create operation')
    }

    await apiClient.createMemory({
      context_key: data.context_key,
      context_value: data.context_value,
      description: data.description,
      token: adminToken
    })
    
    await refreshData() // Refresh data after successful create
    console.log('Memory created successfully:', data.context_key)
  }

  const handleUpdateMemory = async (data: {
    context_key: string
    context_value: any
    description?: string
  }) => {
    const adminToken = getAdminToken()
    if (!adminToken) {
      throw new Error('No admin token available for update operation')
    }

    await apiClient.updateMemory(data.context_key, {
      context_value: data.context_value,
      description: data.description,
      token: adminToken
    })
    
    await refreshData() // Refresh data after successful update
    setEditModalOpen(false)
    setSelectedMemory(null)
    console.log('Memory updated successfully:', data.context_key)
  }

  if (!isConnected) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <Network className="h-12 w-12 text-muted-foreground mx-auto" />
          <div>
            <h3 className="text-lg font-medium text-foreground mb-2">No Server Connection</h3>
            <p className="text-muted-foreground text-sm">Connect to an MCP server to manage memories</p>
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
          <p className="text-muted-foreground text-sm">Loading memories...</p>
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
    <div className="w-full space-y-[var(--space-fluid-lg)] -mx-[var(--container-padding)] px-[var(--container-padding)] -my-[var(--space-fluid-lg)] py-[var(--space-fluid-lg)]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-fluid-2xl font-bold text-foreground">Memory Bank</h1>
          <p className="text-muted-foreground text-fluid-base mt-1">Manage system context and memories</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <Badge variant="outline" className="text-xs bg-primary/15 text-primary border-primary/30 font-medium">
            <div className="w-2 h-2 bg-primary rounded-full mr-2 animate-pulse" />
            {activeServer?.name}
          </Badge>
          {data?.timestamp && (
            <span className="text-xs text-muted-foreground">
              Last updated: {new Date(data.timestamp).toLocaleTimeString()}
            </span>
          )}
          <Button 
            variant="outline" 
            size="sm" 
            onClick={refreshData}
            disabled={loading}
            className="text-xs"
          >
            <RefreshCw className={cn("h-3.5 w-3.5 mr-1.5", loading && "animate-spin")} />
            Refresh
          </Button>
          <CreateMemoryModal onCreateMemory={handleCreateMemory} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-[var(--space-fluid-md)] grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
        <StatsCard 
          icon={Database} 
          label="Total" 
          value={stats.total} 
          change={stats.total > 0 ? `${memories.length} entries` : undefined}
          trend="neutral"
        />
        <StatsCard 
          icon={CheckCircle2} 
          label="Healthy" 
          value={stats.total - stats.stale - stats.errors} 
          change={stats.total > 0 ? `${Math.round(((stats.total - stats.stale - stats.errors)/stats.total)*100)}%` : "0%"}
          trend="up"
        />
        <StatsCard 
          icon={Clock} 
          label="Stale" 
          value={stats.stale} 
          change={stats.stale > 0 ? "Need review" : "All fresh"}
          trend={stats.stale > 0 ? "down" : "neutral"}
        />
        <StatsCard 
          icon={AlertCircle} 
          label="Issues" 
          value={stats.errors + stats.large} 
          change={stats.errors + stats.large > 0 ? "Need attention" : "All good"}
          trend={stats.errors + stats.large > 0 ? "down" : "neutral"}
        />
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-[var(--space-fluid-sm)]">
        <div className="relative flex-1 sm:max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search memories..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 bg-background border-border text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:ring-primary/20 transition-all"
          />
        </div>
        <Select value={sortBy} onValueChange={setSortBy}>
          <SelectTrigger className="w-full sm:w-40 bg-background border-border text-foreground">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-background border-border">
            <SelectItem value="last_updated">Latest First</SelectItem>
            <SelectItem value="key">Alphabetical</SelectItem>
            <SelectItem value="size">Size (Large First)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Memories Table */}
      <div className="bg-card/30 border border-border/50 rounded-lg backdrop-blur-sm overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-border/50 hover:bg-transparent">
              <TableHead className="text-muted-foreground font-medium text-xs uppercase tracking-wider">Memory Key</TableHead>
              <TableHead className="text-muted-foreground font-medium text-xs uppercase tracking-wider">Value</TableHead>
              <TableHead className="text-muted-foreground font-medium text-xs uppercase tracking-wider">Status</TableHead>
              <TableHead className="text-muted-foreground font-medium text-xs uppercase tracking-wider">Updated</TableHead>
              <TableHead className="text-muted-foreground font-medium text-xs uppercase tracking-wider w-24">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredMemories.map((memory) => (
              <MemoryRow
                key={memory.context_key}
                memory={memory}
                onView={handleView}
                onEdit={handleEdit}
                onDelete={handleDelete}
              />
            ))}
          </TableBody>
        </Table>
        
        {filteredMemories.length === 0 && (
          <div className="p-12 text-center">
            <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">No memories found</h3>
            <p className="text-muted-foreground text-sm mb-4">
              {memories.length === 0 ? "Create your first memory to get started" : "No memories match your current filters"}
            </p>
            {memories.length === 0 && (
              <CreateMemoryModal 
                onCreateMemory={handleCreateMemory}
                trigger={
                  <Button>
                    <Plus className="h-4 w-4 mr-2" />
                    Create First Memory
                  </Button>
                }
              />
            )}
          </div>
        )}
      </div>

      {/* Error Display */}
      {operationError && (
        <div className="fixed bottom-4 right-4 bg-destructive/90 text-destructive-foreground px-4 py-2 rounded-lg shadow-lg z-50">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm">{operationError}</span>
            <button 
              onClick={() => setOperationError(null)}
              className="ml-2 hover:bg-destructive-foreground/20 rounded p-1"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {isOperationLoading && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 shadow-xl">
            <div className="flex items-center gap-3">
              <div className="animate-spin h-5 w-5 border-2 border-primary border-t-transparent rounded-full" />
              <span className="text-sm font-medium">Processing...</span>
            </div>
          </div>
        </div>
      )}

      {/* View Memory Modal */}
      <ViewMemoryModal 
        memory={selectedMemory}
        open={viewModalOpen}
        onOpenChange={setViewModalOpen}
      />

      {/* Edit Memory Modal - Using CreateMemoryModal with default values */}
      {selectedMemory && editModalOpen && (
        <EditMemoryModal
          memory={selectedMemory}
          open={editModalOpen}
          onOpenChange={setEditModalOpen}
          onUpdateMemory={handleUpdateMemory}
        />
      )}
    </div>
  )
}