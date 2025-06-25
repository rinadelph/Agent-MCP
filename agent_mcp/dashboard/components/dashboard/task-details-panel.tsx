"use client"

import React, { useState } from 'react'
import { X, Clock, User, Hash, AlertCircle, CheckCircle2, Activity, MessageSquare, GitBranch, Target, Zap, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { Task } from '@/lib/api'
import { useDataStore } from '@/lib/stores/data-store'

interface TaskDetailsPanelProps {
  task: Task | null
  onClose: () => void
}

export function TaskDetailsPanel({ task, onClose }: TaskDetailsPanelProps) {
  const { data } = useDataStore()
  const [activeTab, setActiveTab] = useState<'details' | 'history'>('details')

  // Get task history and related actions
  const taskHistory = task ? (data?.actions || []).filter(action => 
    action.task_id === task.task_id
  ).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()) : []

  // Get agent info if task is assigned
  const assignedAgent = task?.assigned_to ? data?.agents.find(a => a.agent_id === task.assigned_to) : null

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return date.toLocaleDateString()
  }

  const getStatusColor = (status: Task['status']) => {
    const colors = {
      pending: 'bg-amber-500/15 text-amber-600 border-amber-500/30',
      in_progress: 'bg-blue-500/15 text-blue-600 border-blue-500/30',
      completed: 'bg-green-500/15 text-green-600 border-green-500/30',
      cancelled: 'bg-gray-500/15 text-gray-600 border-gray-500/30',
      failed: 'bg-red-500/15 text-red-600 border-red-500/30'
    }
    return colors[status] || colors.pending
  }

  const getPriorityColor = (priority: Task['priority']) => {
    const colors = {
      low: 'bg-slate-500/15 text-slate-600 border-slate-500/30',
      medium: 'bg-amber-500/15 text-amber-600 border-amber-500/30',
      high: 'bg-red-500/15 text-red-600 border-red-500/30'
    }
    return colors[priority] || colors.medium
  }

  const getActionIcon = (actionType: string) => {
    if (actionType.includes('create')) return <Target className="h-3.5 w-3.5 text-blue-500" />
    if (actionType.includes('start') || actionType.includes('begin')) return <Activity className="h-3.5 w-3.5 text-green-500" />
    if (actionType.includes('complete') || actionType.includes('finish')) return <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
    if (actionType.includes('fail') || actionType.includes('error')) return <AlertCircle className="h-3.5 w-3.5 text-red-500" />
    if (actionType.includes('update') || actionType.includes('modify')) return <Zap className="h-3.5 w-3.5 text-amber-500" />
    return <ChevronRight className="h-3.5 w-3.5 text-gray-500" />
  }

  // Parse JSON fields safely
  const parseJsonField = (field: unknown): unknown[] => {
    if (Array.isArray(field)) return field
    if (typeof field === 'string') {
      try {
        return JSON.parse(field)
      } catch {
        return []
      }
    }
    return []
  }

  const dependencies = task ? parseJsonField(task.depends_on_tasks) : []
  const childTasks = task ? parseJsonField(task.child_tasks) : []
  const notes = task ? parseJsonField(task.notes) : []

  return (
    <div className={cn(
      "fixed right-0 top-0 h-screen bg-background border-l transform transition-all duration-500 z-30",
      "shadow-lg",
      task ? "translate-x-0 w-[420px]" : "translate-x-full w-0"
    )}>
      {task && (
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className="bg-card border-b px-4 py-3">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h2 className="text-base font-semibold truncate">{task.title}</h2>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="outline" className={cn("text-xs", getStatusColor(task.status))}>
                    {task.status.replace('_', ' ')}
                  </Badge>
                  <Badge variant="outline" className={cn("text-xs", getPriorityColor(task.priority))}>
                    {task.priority}
                  </Badge>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="h-7 w-7 flex-shrink-0 ml-2"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b bg-muted/30">
            <button
              onClick={() => setActiveTab('details')}
              className={cn(
                "flex-1 px-4 py-2 text-sm font-medium transition-colors",
                activeTab === 'details' 
                  ? "text-foreground border-b-2 border-primary bg-background" 
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              Details
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={cn(
                "flex-1 px-4 py-2 text-sm font-medium transition-colors",
                activeTab === 'history' 
                  ? "text-foreground border-b-2 border-primary bg-background" 
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              History ({taskHistory.length})
            </button>
          </div>

          <ScrollArea className="flex-1">
            <div className="px-4 py-4 space-y-4">
              
              {activeTab === 'details' && (
                <>
                  {/* Basic Info */}
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground text-xs uppercase tracking-wider">Task ID</span>
                      <p className="font-mono text-xs mt-1 break-all">{task.task_id}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground text-xs uppercase tracking-wider">Created</span>
                      <p className="text-sm mt-1">{new Date(task.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>

                  {/* Assigned Agent */}
                  {assignedAgent && (
                    <div>
                      <span className="text-muted-foreground text-xs uppercase tracking-wider">Assigned Agent</span>
                      <div className="bg-muted rounded-lg p-3 mt-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium">{assignedAgent.agent_id}</span>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {assignedAgent.status}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Description */}
                  {task.description && (
                    <div>
                      <span className="text-muted-foreground text-xs uppercase tracking-wider">Description</span>
                      <p className="text-sm mt-2 whitespace-pre-wrap">{task.description}</p>
                    </div>
                  )}

                  {/* Dependencies */}
                  {dependencies.length > 0 && (
                    <div>
                      <span className="text-muted-foreground text-xs uppercase tracking-wider">Dependencies</span>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {dependencies.map((depId: any, index) => (
                          <Badge key={index} variant="outline" className="text-xs font-mono">
                            <GitBranch className="h-3 w-3 mr-1" />
                            {depId}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Child Tasks */}
                  {childTasks.length > 0 && (
                    <div>
                      <span className="text-muted-foreground text-xs uppercase tracking-wider">Subtasks</span>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {childTasks.map((childId: any, index) => (
                          <Badge key={index} variant="outline" className="text-xs font-mono">
                            <Hash className="h-3 w-3 mr-1" />
                            {childId}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Notes */}
                  {notes.length > 0 && (
                    <div>
                      <span className="text-muted-foreground text-xs uppercase tracking-wider">Notes</span>
                      <div className="space-y-2 mt-2">
                        {notes.map((note: any, index) => (
                          <div key={index} className="bg-muted/50 rounded-lg p-3">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs font-medium">{note.author}</span>
                              <span className="text-xs text-muted-foreground">
                                {new Date(note.timestamp).toLocaleString()}
                              </span>
                            </div>
                            <p className="text-sm">{note.content}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Timestamps */}
                  <div className="pt-4 border-t space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Created</span>
                      <span className="font-mono text-xs">{new Date(task.created_at).toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Last Updated</span>
                      <span className="font-mono text-xs">{new Date(task.updated_at).toLocaleString()}</span>
                    </div>
                  </div>
                </>
              )}

              {activeTab === 'history' && (
                <div className="space-y-3">
                  {taskHistory.length > 0 ? (
                    taskHistory.map((action, index) => (
                      <div key={index} className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted/30 transition-colors">
                        <div className="flex-shrink-0 mt-0.5">
                          {getActionIcon(action.action_type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <p className="font-medium text-sm capitalize">
                              {action.action_type.replace(/_/g, ' ')}
                            </p>
                            <span className="text-xs text-muted-foreground flex-shrink-0">
                              {formatTimestamp(action.timestamp)}
                            </span>
                          </div>
                          {action.agent_id && (
                            <p className="text-xs text-muted-foreground mt-1">
                              Agent: {action.agent_id}
                            </p>
                          )}
                          {action.details && (
                            <p className="text-xs text-muted-foreground mt-1 break-words">
                              {action.details}
                            </p>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8">
                      <Clock className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">No history available</p>
                    </div>
                  )}
                </div>
              )}

            </div>
          </ScrollArea>

          {/* Action Buttons */}
          <div className="border-t p-4 space-y-2">
            {task.status === 'pending' && (
              <Button className="w-full" size="sm">
                <Activity className="h-3.5 w-3.5 mr-2" />
                Start Task
              </Button>
            )}
            {task.status === 'in_progress' && (
              <Button className="w-full" variant="secondary" size="sm">
                <CheckCircle2 className="h-3.5 w-3.5 mr-2" />
                Mark Complete
              </Button>
            )}
            <Button variant="outline" className="w-full" size="sm">
              <MessageSquare className="h-3.5 w-3.5 mr-2" />
              Add Note
            </Button>
          </div>

        </div>
      )}
    </div>
  )
}