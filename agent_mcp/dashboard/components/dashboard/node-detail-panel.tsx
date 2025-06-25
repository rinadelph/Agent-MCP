"use client"

import React, { useEffect, useState } from 'react'
import { X, User, FileText, Activity, Clock, AlertCircle, CheckCircle, XCircle, Loader2, ChevronRight, Zap, Target, GitBranch, FileCode, Hash, Shield, Database, Copy } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { apiClient, Agent, Task } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useDataStore } from '@/lib/stores/data-store'

interface NodeDetailPanelProps {
  nodeId: string | null
  nodeType: 'agent' | 'task' | 'context' | 'file' | 'admin' | null
  isOpen: boolean
  onClose: () => void
  nodeData?: any
}

const statusIcons = {
  pending: Clock,
  running: Loader2,
  in_progress: Loader2,
  completed: CheckCircle,
  terminated: XCircle,
  failed: AlertCircle,
  cancelled: XCircle
}

const statusColors = {
  pending: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/30',
  running: 'bg-blue-500/10 text-blue-600 border-blue-500/30',
  in_progress: 'bg-blue-500/10 text-blue-600 border-blue-500/30',
  completed: 'bg-green-500/10 text-green-600 border-green-500/30',
  terminated: 'bg-red-500/10 text-red-600 border-red-500/30',
  failed: 'bg-red-500/10 text-red-600 border-red-500/30',
  cancelled: 'bg-gray-500/10 text-gray-600 border-gray-500/30'
}

const priorityColors = {
  low: 'bg-slate-500/10 text-slate-600 border-slate-500/30',
  medium: 'bg-amber-500/10 text-amber-600 border-amber-500/30',
  high: 'bg-red-500/10 text-red-600 border-red-500/30'
}

export function NodeDetailPanel({ nodeId, nodeType, isOpen, onClose, nodeData }: NodeDetailPanelProps) {
  const [loading, setLoading] = useState(false)
  const [details, setDetails] = useState<Agent | Task | any | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { data, fetchAllData, getAgent, getTask, getContext, getAdminToken } = useDataStore()

  useEffect(() => {
    if (!nodeId || !nodeType || !isOpen) return

    const loadDetails = async () => {
      setLoading(true)
      setError(null)
      
      try {
        // Ensure we have data loaded
        if (!data) {
          await fetchAllData()
        }

        let detailData = null
        
        if (nodeType === 'agent') {
          detailData = getAgent(nodeId)
        } else if (nodeType === 'task') {
          detailData = getTask(nodeId)
        } else if (nodeType === 'context') {
          detailData = getContext(nodeId)
        } else if (nodeType === 'admin') {
          // Special handling for admin
          detailData = {
            agent_id: 'Admin',
            name: 'System Administrator',
            status: 'active',
            auth_token: getAdminToken(),
            capabilities: ['All permissions'],
            created_at: 'System'
          }
        }
        
        if (detailData) {
          setDetails(detailData)
        } else {
          // Fallback to API if not in cache
          const fullNodeId = nodeType === 'task' && !nodeId.startsWith('task_') 
            ? `task_${nodeId}` 
            : nodeType === 'agent' && !nodeId.startsWith('agent_')
            ? `agent_${nodeId}`
            : nodeId
            
          const nodeDetails = await apiClient.getNodeDetails(fullNodeId)
          
          if (nodeDetails.data) {
            setDetails(nodeDetails.data)
          } else {
            throw new Error(`${nodeType} details not found`)
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load details')
      } finally {
        setLoading(false)
      }
    }

    loadDetails()
  }, [nodeId, nodeType, isOpen, data, fetchAllData, getAgent, getTask, getContext, getAdminToken])

  if (!isOpen) return null

  const renderAgentDetails = (agent: Agent) => {
    const StatusIcon = statusIcons[agent.status] || Activity
    const isActive = agent.status === 'running'

    return (
      <>
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-primary/10">
              <User className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">{agent.agent_id}</h3>
              <p className="text-sm text-muted-foreground">Agent ID</p>
            </div>
          </div>
          <Badge variant="outline" className={cn(statusColors[agent.status])}>
            <StatusIcon className={cn("h-3 w-3 mr-1", isActive && "animate-spin")} />
            {agent.status}
          </Badge>
        </div>

        <Separator className="mb-4" />

        {/* Agent Info */}
        <div className="space-y-4">
          {/* Current Task */}
          {agent.current_task && (
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Current Task</span>
              </div>
              <span className="text-sm text-muted-foreground">{agent.current_task}</span>
            </div>
          )}

          {/* Working Directory */}
          {agent.working_directory && (
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2">
                <FileCode className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Working Directory</span>
              </div>
              <span className="text-sm text-muted-foreground font-mono">{agent.working_directory}</span>
            </div>
          )}

          {/* Auth Token (for admin or if available) */}
          {agent.auth_token && (
            <div className="p-3 rounded-lg bg-muted/50 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Authentication Token</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(agent.auth_token!)
                  }}
                  className="h-7 px-2"
                >
                  <Copy className="h-3 w-3 mr-1" />
                  Copy
                </Button>
              </div>
              <div className="font-mono text-xs bg-background/50 p-2 rounded break-all">
                {agent.auth_token}
              </div>
            </div>
          )}

          {/* Capabilities */}
          {agent.capabilities && (() => {
            // Parse capabilities if it's a string
            let capabilities: string[] = []
            try {
              if (typeof agent.capabilities === 'string') {
                capabilities = JSON.parse(agent.capabilities)
              } else if (Array.isArray(agent.capabilities)) {
                capabilities = agent.capabilities
              }
            } catch {
              capabilities = []
            }
            
            return capabilities.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Capabilities</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {capabilities.map((cap, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {cap}
                    </Badge>
                  ))}
                </div>
              </div>
            )
          })()}

          {/* Timestamps */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Created</span>
              <span className="font-mono">{new Date(agent.created_at).toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Last Updated</span>
              <span className="font-mono">{new Date(agent.updated_at).toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 flex gap-2">
          {agent.status === 'running' && (
            <Button variant="destructive" size="sm" className="flex-1">
              Terminate Agent
            </Button>
          )}
          <Button variant="outline" size="sm" className="flex-1">
            View Logs
          </Button>
        </div>
      </>
    )
  }

  const renderTaskDetails = (task: Task) => {
    const StatusIcon = statusIcons[task.status] || Activity
    const isActive = task.status === 'in_progress'

    return (
      <>
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-primary/10">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold line-clamp-2">{task.title || 'Untitled Task'}</h3>
              <p className="text-sm text-muted-foreground">
                Task #{task.task_id ? task.task_id.slice(0, 8) : 'unknown'}
              </p>
            </div>
          </div>
        </div>

        {/* Status and Priority */}
        <div className="flex gap-2 mb-4">
          <Badge variant="outline" className={cn(statusColors[task.status])}>
            <StatusIcon className={cn("h-3 w-3 mr-1", isActive && "animate-spin")} />
            {task.status}
          </Badge>
          <Badge variant="outline" className={cn(priorityColors[task.priority])}>
            {task.priority} priority
          </Badge>
        </div>

        <Separator className="mb-4" />

        {/* Task Info */}
        <ScrollArea className="h-[300px] pr-4">
          <div className="space-y-4">
            {/* Description */}
            {task.description && (
              <div className="space-y-2">
                <span className="text-sm font-medium">Description</span>
                <p className="text-sm text-muted-foreground">{task.description}</p>
              </div>
            )}

            {/* Assigned To */}
            {task.assigned_to && (
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Assigned To</span>
                </div>
                <span className="text-sm text-muted-foreground">{task.assigned_to}</span>
              </div>
            )}

            {/* Dependencies */}
            {task.depends_on_tasks && (() => {
              // Parse depends_on_tasks if it's a string
              let dependencies: string[] = []
              try {
                if (typeof task.depends_on_tasks === 'string') {
                  dependencies = JSON.parse(task.depends_on_tasks)
                } else if (Array.isArray(task.depends_on_tasks)) {
                  dependencies = task.depends_on_tasks
                }
              } catch {
                dependencies = []
              }
              
              return dependencies.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <GitBranch className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Dependencies</span>
                  </div>
                  <div className="space-y-1">
                    {dependencies.map((depId) => (
                      <div key={depId} className="flex items-center gap-2 text-sm text-muted-foreground">
                        <ChevronRight className="h-3 w-3" />
                        <span className="font-mono">{depId.slice(0, 8)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })()}

            {/* Child Tasks */}
            {task.child_tasks && (() => {
              // Parse child_tasks if it's a string
              let childTasks: string[] = []
              try {
                if (typeof task.child_tasks === 'string') {
                  childTasks = JSON.parse(task.child_tasks)
                } else if (Array.isArray(task.child_tasks)) {
                  childTasks = task.child_tasks
                }
              } catch {
                childTasks = []
              }
              
              return childTasks.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Hash className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Subtasks ({childTasks.length})</span>
                  </div>
                  <Progress value={33} className="h-2" />
                </div>
              )
            })()}

            {/* Notes */}
            {task.notes && (() => {
              // Parse notes if it's a string
              let notes: Array<{timestamp: string, author: string, content: string}> = []
              try {
                if (typeof task.notes === 'string') {
                  notes = JSON.parse(task.notes)
                } else if (Array.isArray(task.notes)) {
                  notes = task.notes
                }
              } catch {
                notes = []
              }
              
              return notes.length > 0 && (
                <div className="space-y-2">
                  <span className="text-sm font-medium">Notes</span>
                  <div className="space-y-2">
                    {notes.map((note, idx) => (
                      <div key={idx} className="p-3 rounded-lg bg-muted/30 space-y-1">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>{note.author}</span>
                          <span>{new Date(note.timestamp).toLocaleString()}</span>
                        </div>
                        <p className="text-sm">{note.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })()}

            {/* Timestamps */}
            <div className="space-y-2 pt-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Created</span>
                <span className="font-mono">{new Date(task.created_at).toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Last Updated</span>
                <span className="font-mono">{new Date(task.updated_at).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </ScrollArea>

        {/* Actions */}
        <div className="mt-6 flex gap-2">
          {task.status === 'pending' && (
            <Button variant="default" size="sm" className="flex-1">
              Start Task
            </Button>
          )}
          {task.status === 'in_progress' && (
            <Button variant="secondary" size="sm" className="flex-1">
              Mark Complete
            </Button>
          )}
          <Button variant="outline" size="sm" className="flex-1">
            Edit Task
          </Button>
        </div>
      </>
    )
  }

  const renderContextDetails = (context: any) => {
    return (
      <>
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-primary/10">
              <Database className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">{context.context_key}</h3>
              <p className="text-sm text-muted-foreground">Context Entry</p>
            </div>
          </div>
        </div>

        <Separator className="mb-4" />

        {/* Context Info */}
        <div className="space-y-4">
          {/* Value */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Value</span>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <pre className="text-sm whitespace-pre-wrap break-all">
                {typeof context.context_value === 'string' 
                  ? context.context_value 
                  : JSON.stringify(context.context_value, null, 2)}
              </pre>
            </div>
          </div>

          {/* Summary */}
          {context.summary && (
            <div className="space-y-2">
              <span className="text-sm font-medium">Summary</span>
              <p className="text-sm text-muted-foreground">{context.summary}</p>
            </div>
          )}

          {/* Metadata */}
          {context.metadata && (
            <div className="space-y-2">
              <span className="text-sm font-medium">Metadata</span>
              <div className="p-3 rounded-lg bg-muted/50">
                <pre className="text-sm whitespace-pre-wrap">
                  {JSON.stringify(context.metadata, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Created</span>
              <span className="font-mono">{context.created_at ? new Date(context.created_at).toLocaleString() : 'N/A'}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Last Updated</span>
              <span className="font-mono">{context.updated_at ? new Date(context.updated_at).toLocaleString() : 'N/A'}</span>
            </div>
          </div>
        </div>
      </>
    )
  }

  return (
    <div className={cn(
      "fixed right-0 top-16 h-[calc(100vh-4rem)] bg-background border-l transform transition-all duration-500 z-30",
      "shadow-lg",
      isOpen ? "translate-x-0 w-[384px]" : "translate-x-full w-0"
    )}>
      {isOpen && (
        <div className="h-full flex flex-col">
          {/* Header - Compact like agents dashboard */}
          <div className="bg-card border-b px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold">
                  {nodeType === 'agent' || nodeType === 'admin' ? 'Agent Details' : 
                   nodeType === 'task' ? 'Task Details' : 
                   nodeType === 'context' ? 'Context Details' :
                   'Node Details'}
                </h2>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="h-7 w-7"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <ScrollArea className="flex-1">
            <div className="px-6 py-4 space-y-4">
            {loading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            )}

            {error && (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <AlertCircle className="h-8 w-8 text-destructive mb-2" />
                <p className="text-sm text-destructive">{error}</p>
              </div>
            )}

            {details && !loading && !error && (
              <>
                {(nodeType === 'agent' || nodeType === 'admin') && renderAgentDetails(details as Agent)}
                {nodeType === 'task' && renderTaskDetails(details as Task)}
                {nodeType === 'context' && renderContextDetails(details)}
              </>
            )}

            {!details && !loading && !error && nodeData && (
              <div className="space-y-4">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 rounded-full bg-primary/10">
                    <Hash className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold">{nodeData.label || nodeId}</h3>
                    <p className="text-sm text-muted-foreground capitalize">{nodeType}</p>
                  </div>
                </div>
                <Separator />
                <div className="text-sm text-muted-foreground">
                  <p>No additional details available for this node type.</p>
                </div>
              </div>
            )}
            </div>
          </ScrollArea>
        </div>
      )}
    </div>
  )
}