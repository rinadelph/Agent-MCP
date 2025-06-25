"use client"

import React from 'react'
import { Copy, Eye, Clock, User, Database, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import type { Memory } from '@/lib/api'

interface ViewMemoryModalProps {
  memory: Memory | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ViewMemoryModal({ memory, open, onOpenChange }: ViewMemoryModalProps) {
  if (!memory) return null

  const formatValue = (value: any) => {
    if (typeof value === 'string') {
      return value
    }
    return JSON.stringify(value, null, 2)
  }

  const copyToClipboard = async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text)
      // TODO: Add toast notification
      console.log(`${type} copied to clipboard`)
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
    }
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return {
        relative: getRelativeTime(date),
        absolute: date.toLocaleString()
      }
    } catch {
      return {
        relative: 'Unknown',
        absolute: dateString
      }
    }
  }

  const getRelativeTime = (date: Date) => {
    const now = new Date()
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)
    
    if (diffInSeconds < 60) return 'Just now'
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`
    if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)} days ago`
    return `${Math.floor(diffInSeconds / 2592000)} months ago`
  }

  const metadata = memory._metadata
  const dateInfo = formatDate(memory.last_updated)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl bg-card border-border text-card-foreground max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Eye className="h-5 w-5 text-primary" />
            <DialogTitle className="text-lg">Memory Details</DialogTitle>
          </div>
          <DialogDescription className="text-muted-foreground">
            View and inspect memory entry information
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Memory Key */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-foreground">Memory Key</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => copyToClipboard(memory.context_key, 'Memory key')}
                className="h-6 w-6 p-0"
              >
                <Copy className="h-3 w-3" />
              </Button>
            </div>
            <div className="bg-muted/30 border border-border rounded-lg p-3">
              <code className="font-mono text-sm text-foreground">{memory.context_key}</code>
            </div>
          </div>

          {/* Description */}
          {memory.description && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-foreground">Description</h3>
              <div className="bg-muted/30 border border-border rounded-lg p-3">
                <p className="text-sm text-foreground">{memory.description}</p>
              </div>
            </div>
          )}

          {/* Value */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-foreground">Value</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => copyToClipboard(formatValue(memory.value), 'Memory value')}
                className="h-6 w-6 p-0"
              >
                <Copy className="h-3 w-3" />
              </Button>
            </div>
            <div className="bg-muted/30 border border-border rounded-lg p-3 max-h-64 overflow-y-auto">
              <pre className="font-mono text-sm text-foreground whitespace-pre-wrap break-words">
                {formatValue(memory.value)}
              </pre>
            </div>
          </div>

          {/* Metadata */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-foreground">Memory Information</h3>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Last Updated */}
              <div className="bg-muted/30 border border-border rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Last Updated
                  </span>
                </div>
                <div className="text-sm text-foreground">{dateInfo.relative}</div>
                <div className="text-xs text-muted-foreground">{dateInfo.absolute}</div>
              </div>

              {/* Updated By */}
              <div className="bg-muted/30 border border-border rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Updated By
                  </span>
                </div>
                <div className="text-sm text-foreground">{memory.updated_by}</div>
              </div>
            </div>

            {/* Size Information */}
            {metadata && (
              <div className="bg-muted/30 border border-border rounded-lg p-3">
                <div className="flex items-center gap-2 mb-3">
                  <Database className="h-4 w-4 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Storage Information
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Size:</span>
                    <span className="ml-2 text-foreground">{metadata.size_kb} KB</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Bytes:</span>
                    <span className="ml-2 text-foreground">{metadata.size_bytes}</span>
                  </div>
                  {metadata.days_old !== undefined && (
                    <div>
                      <span className="text-muted-foreground">Age:</span>
                      <span className="ml-2 text-foreground">{metadata.days_old} days</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Status Badges */}
            <div className="space-y-2">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Status Indicators
              </h4>
              <div className="flex flex-wrap gap-2">
                {metadata?.json_valid ? (
                  <Badge variant="outline" className="text-xs bg-green-500/15 text-green-600 border-green-500/30">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Valid JSON
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-xs bg-red-500/15 text-red-600 border-red-500/30">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Invalid JSON
                  </Badge>
                )}
                
                {metadata?.is_stale && (
                  <Badge variant="outline" className="text-xs bg-orange-500/15 text-orange-600 border-orange-500/30">
                    <Clock className="h-3 w-3 mr-1" />
                    Stale ({metadata.days_old}+ days)
                  </Badge>
                )}
                
                {metadata?.is_large && (
                  <Badge variant="outline" className="text-xs bg-yellow-500/15 text-yellow-600 border-yellow-500/30">
                    <Database className="h-3 w-3 mr-1" />
                    Large Entry (&gt;10KB)
                  </Badge>
                )}
                
                {!metadata?.is_stale && !metadata?.is_large && metadata?.json_valid && (
                  <Badge variant="outline" className="text-xs bg-green-500/15 text-green-600 border-green-500/30">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Healthy
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer with copy actions */}
        <div className="flex justify-end gap-2 pt-4 border-t border-border">
          <Button
            variant="outline"
            size="sm"
            onClick={() => copyToClipboard(memory.context_key, 'Memory key')}
          >
            <Copy className="h-3 w-3 mr-2" />
            Copy Key
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => copyToClipboard(formatValue(memory.value), 'Memory value')}
          >
            <Copy className="h-3 w-3 mr-2" />
            Copy Value
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => copyToClipboard(
              JSON.stringify({
                key: memory.context_key,
                value: memory.value,
                description: memory.description,
                updated_by: memory.updated_by,
                last_updated: memory.last_updated
              }, null, 2),
              'Full memory data'
            )}
          >
            <Copy className="h-3 w-3 mr-2" />
            Copy All
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}