"use client"

import React, { useState } from 'react'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { SmartValueEditor } from './smart-value-editor'

interface CreateMemoryData {
  context_key: string
  context_value: any
  description?: string
}

interface CreateMemoryModalProps {
  onCreateMemory: (data: CreateMemoryData) => Promise<void>
  trigger?: React.ReactNode
}

export function CreateMemoryModal({ onCreateMemory, trigger }: CreateMemoryModalProps) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    context_key: '',
    context_value: '',
    description: ''
  })

  const handleValueChange = (value: any) => {
    setFormData(prev => ({ ...prev, context_value: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.context_key.trim()) {
      return
    }

    setLoading(true)
    try {
      await onCreateMemory({
        context_key: formData.context_key.trim(),
        context_value: formData.context_value,
        description: formData.description.trim() || undefined
      })

      // Reset form and close modal
      setFormData({ context_key: '', context_value: '', description: '' })
      setOpen(false)
    } catch (error) {
      console.error('Failed to create memory:', error)
      // Error handling would be done by the parent component
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    setFormData({ context_key: '', context_value: '', description: '' })
    setOpen(false)
  }

  // Generate context key suggestions based on common patterns
  const contextKeySuggestions = [
    'api.endpoints.base_url',
    'config.database.connection',
    'settings.ui.theme',
    'memory.system.status',
    'cache.ttl.default'
  ]

  const defaultTrigger = (
    <Button size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg hover:shadow-primary/25 transition-all duration-200">
      <Plus className="h-4 w-4 mr-1.5" />
      New Memory
    </Button>
  )

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || defaultTrigger}
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg bg-card border-border text-card-foreground max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-lg">Create New Memory</DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Add a new memory entry to the context bank. Use structured keys for better organization.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Context Key */}
          <div className="space-y-2">
            <Label htmlFor="context_key" className="text-sm font-medium text-foreground">
              Memory Key
            </Label>
            <Input
              id="context_key"
              value={formData.context_key}
              onChange={(e) => setFormData(prev => ({ ...prev, context_key: e.target.value }))}
              placeholder="e.g., api.config.base_url"
              className="bg-background border-border text-foreground font-mono text-sm"
              required
            />
            <div className="text-xs text-muted-foreground">
              Use dot notation for hierarchical organization (e.g., api.endpoints.users)
            </div>
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

          {/* Common Patterns Helper */}
          <div className="bg-muted/30 border border-border rounded-lg p-3">
            <div className="text-xs font-medium text-foreground mb-2">Common Key Patterns:</div>
            <div className="flex flex-wrap gap-1">
              {contextKeySuggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setFormData(prev => ({ ...prev, context_key: suggestion }))}
                  className="text-xs bg-background hover:bg-muted border border-border rounded px-2 py-1 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          <DialogFooter className="gap-2 pt-4">
            <Button 
              type="button" 
              variant="outline" 
              onClick={handleCancel} 
              size="sm"
              disabled={loading}
            >
              Cancel
            </Button>
            <Button 
              type="submit" 
              size="sm" 
              disabled={loading || !formData.context_key.trim()}
              className="bg-primary hover:bg-primary/90 shadow-lg hover:shadow-primary/25 transition-all"
            >
              {loading ? (
                <>
                  <div className="h-3 w-3 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="h-3 w-3 mr-2" />
                  Create Memory
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}