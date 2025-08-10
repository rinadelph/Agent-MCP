"use client"

import React, { useState } from 'react'
import { X, Copy, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { Agent, Task } from '@/lib/api'
import { useDataStore } from '@/lib/stores/data-store'
import { TaskDetailsDialog } from './task-details-dialog'

interface AgentDetailsPanelProps {
  agent: Agent | null
  onClose: () => void
}

export function AgentDetailsPanel({ agent, onClose }: AgentDetailsPanelProps) {
  const [copiedToken, setCopiedToken] = useState(false)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [taskDialogOpen, setTaskDialogOpen] = useState(false)
  const { getAgentTasks, getAgentActions } = useDataStore()
  
  // Get agent's tasks and actions from cached data
  const agentTasks = agent ? getAgentTasks(agent.agent_id) : []
  const agentActions = agent ? getAgentActions(agent.agent_id) : []
  
  // Get current task details
  const currentTask = agentTasks.find(t => t.task_id === agent?.current_task)
  
  const handleTaskClick = (task: Task) => {
    setSelectedTask(task)
    setTaskDialogOpen(true)
  }

  const copyToken = () => {
    if (agent?.auth_token) {
      navigator.clipboard.writeText(agent.auth_token)
      setCopiedToken(true)
      setTimeout(() => setCopiedToken(false), 2000)
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return date.toLocaleDateString()
  }

  const getStatusColor = (status: Agent['status']) => {
    const colors = {
      running: 'bg-primary/15 text-primary border-primary/30',
      pending: 'bg-warning/15 text-warning border-warning/30',
      terminated: 'bg-muted/50 text-muted-foreground border-border',
      failed: 'bg-destructive/15 text-destructive border-destructive/30'
    }
    return colors[status] || colors.pending
  }


  return (
    <div className={cn(
      "fixed right-0 top-16 h-[calc(100vh-4rem)] bg-background border-l transform transition-all duration-500 z-30",
      "shadow-lg",
      agent ? "translate-x-0 w-[360px]" : "translate-x-full w-0"
    )}>
      {agent && (
        <div className="h-full flex flex-col">
          {/* Header - Compact */}
          <div className="bg-card border-b px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold">{agent.agent_id}</h2>
                <Badge 
                  variant="outline" 
                  className={cn("text-xs", getStatusColor(agent.status))}
                >
                  {agent.status}
                </Badge>
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

              {/* Token Section */}
              {agent.auth_token && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-3">Authentication Token</h3>
                  <div className="bg-muted rounded-lg p-3 border border-border">
                    <div className="flex items-center justify-between gap-2">
                      <code className="text-xs font-mono truncate flex-1">{agent.auth_token}</code>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={copyToken}
                        className="h-6 px-2 shrink-0"
                      >
                        {copiedToken ? (
                          <CheckCircle2 className="h-3 w-3 text-green-500" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {/* Current Task Section */}
              {currentTask && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-3">Current Task</h3>
                  <div className="bg-muted rounded-lg p-4 border border-border">
                    <p className="text-sm font-medium text-foreground mb-2">{currentTask.title}</p>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>ID: {currentTask.task_id.slice(-8)}</span>
                      <Badge variant="outline" className="text-xs">{currentTask.status}</Badge>
                    </div>
                    {currentTask.description && (
                      <p className="text-xs text-muted-foreground mt-2">{currentTask.description}</p>
                    )}
                  </div>
                </div>
              )}

              {/* Recent Actions */}
              {agentActions.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-3">Recent Activity</h3>
                  <div className="space-y-2">
                    {agentActions.slice(0, 10).map((action, index) => (
                      <div key={index} className="flex items-start gap-3 text-sm">
                        <div className="flex-shrink-0 mt-0.5">
                          <div className={cn(
                            "w-2 h-2 rounded-full",
                            action.action_type === 'task_completed' ? 'bg-green-500' :
                            action.action_type === 'task_failed' ? 'bg-destructive' :
                            action.action_type.includes('create') ? 'bg-primary' : 'bg-muted-foreground'
                          )} />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <p className="font-medium">{action.action_type.replace(/_/g, ' ')}</p>
                            <span className="text-xs text-muted-foreground">{formatTimestamp(action.timestamp)}</span>
                          </div>
                          {action.task_id && (
                            <p className="text-xs text-muted-foreground mt-0.5">Task: {action.task_id.slice(-8)}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* All Tasks */}
              {agentTasks.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-3">All Tasks ({agentTasks.length})</h3>
                  <div className="space-y-2">
                    {agentTasks.map((task) => (
                      <button
                        key={task.task_id}
                        onClick={() => handleTaskClick(task)}
                        className="bg-muted rounded-lg p-3 border border-border hover:bg-muted/80 transition-colors w-full text-left"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="text-sm font-medium">{task.title}</p>
                            <p className="text-xs text-muted-foreground mt-1">ID: {task.task_id.slice(-8)}</p>
                          </div>
                          <Badge variant="outline" className="text-xs ml-2">
                            {task.status}
                          </Badge>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Agent Info */}
              <div className="pt-4 border-t">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Agent ID</span>
                    <span className="font-mono">{agent.agent_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Created</span>
                    <span>{new Date(agent.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status</span>
                    <Badge variant="outline" className="text-xs">{agent.status}</Badge>
                  </div>
                </div>
              </div>
            </div>
          </ScrollArea>

        </div>
      )}
      
      {/* Task Details Dialog */}
      <TaskDetailsDialog
        task={selectedTask}
        open={taskDialogOpen}
        onOpenChange={(open) => {
          setTaskDialogOpen(open)
          if (!open) setSelectedTask(null)
        }}
      />
    </div>
  )
}