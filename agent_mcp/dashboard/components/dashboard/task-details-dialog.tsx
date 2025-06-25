"use client"

import React from 'react'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Task } from '@/lib/api'
import { cn } from '@/lib/utils'

interface TaskDetailsDialogProps {
  task: Task | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TaskDetailsDialog({ task, open, onOpenChange }: TaskDetailsDialogProps) {
  if (!task) return null

  // Helper function to parse JSON fields safely
  const parseJsonField = (field: any): any[] => {
    if (!field) return []
    if (Array.isArray(field)) return field
    if (typeof field === 'string') {
      try {
        const parsed = JSON.parse(field)
        return Array.isArray(parsed) ? parsed : []
      } catch {
        return []
      }
    }
    return []
  }

  const getStatusColor = (status: Task['status']) => {
    const colors = {
      pending: 'bg-warning/15 text-warning border-warning/30',
      in_progress: 'bg-primary/15 text-primary border-primary/30',
      completed: 'bg-green-500/15 text-green-600 border-green-500/30',
      cancelled: 'bg-muted/50 text-muted-foreground border-border',
      failed: 'bg-destructive/15 text-destructive border-destructive/30'
    }
    return colors[status] || colors.pending
  }

  const getPriorityColor = (priority: Task['priority']) => {
    const colors = {
      low: 'bg-muted text-muted-foreground',
      medium: 'bg-primary/10 text-primary',
      high: 'bg-destructive/10 text-destructive'
    }
    return colors[priority] || colors.medium
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between pr-8">
            <span className="text-lg font-semibold">{task.title}</span>
            <Badge variant="outline" className={cn("text-xs", getStatusColor(task.status))}>
              {task.status.replace(/_/g, ' ')}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh] pr-4">
          <div className="space-y-4">
            {/* Task Info */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Task ID</span>
                <p className="font-mono text-xs mt-1">{task.task_id}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Priority</span>
                <Badge variant="outline" className={cn("text-xs mt-1", getPriorityColor(task.priority))}>
                  {task.priority}
                </Badge>
              </div>
              <div>
                <span className="text-muted-foreground">Assigned To</span>
                <p className="text-sm mt-1">{task.assigned_to || 'Unassigned'}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Created</span>
                <p className="text-sm mt-1">{new Date(task.created_at).toLocaleDateString()}</p>
              </div>
            </div>

            <Separator />

            {/* Description */}
            {task.description && (
              <>
                <div>
                  <h4 className="text-sm font-semibold mb-2">Description</h4>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{task.description}</p>
                </div>
                <Separator />
              </>
            )}

            {/* Notes */}
            {(() => {
              const notes = parseJsonField(task.notes)
              return notes.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold mb-3">Notes</h4>
                  <div className="space-y-3">
                    {notes.map((note, index) => (
                      <div key={index} className="bg-muted rounded-lg p-3">
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
              )
            })()}

            {/* Dependencies */}
            {(() => {
              const dependencies = parseJsonField(task.depends_on_tasks)
              return dependencies.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Dependencies</h4>
                    <div className="flex flex-wrap gap-2">
                      {dependencies.map((depId, index) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {depId}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </>
              )
            })()}

            {/* Child Tasks */}
            {(() => {
              const childTasks = parseJsonField(task.child_tasks)
              return childTasks.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Subtasks</h4>
                    <div className="flex flex-wrap gap-2">
                      {childTasks.map((childId, index) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {childId}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </>
              )
            })()}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}