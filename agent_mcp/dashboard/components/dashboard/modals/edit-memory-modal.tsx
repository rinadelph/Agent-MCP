"use client"

import React, { useState, useEffect } from 'react'
import { Save, X } from 'lucide-react'
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
} from '@/components/ui/dialog'
import type { Memory } from '@/lib/api'

interface EditMemoryData {
  context_key: string
  context_value: any
  description?: string
}

interface EditMemoryModalProps {
  memory: Memory | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaveMemory: (memory: Memory, data: EditMemoryData) => Promise<void>
}

export function EditMemoryModal({ memory, open, onOpenChange, onSaveMemory }: EditMemoryModalProps) {
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    context_key: '',
    context_value: '',
    description: ''
  })
  const [jsonError, setJsonError] = useState<string | null>(null)

  // Pre-populate form fields when memory changes
  useEffect(() => {
    if (memory) {
      setFormData({
        context_key: memory.context_key,
        context_value: typeof memory.value === 'string' ? memory.value : JSON.stringify(memory.value, null, 2),
        description: memory.description || ''
      })
      setJsonError(null)
    }
  }, [memory])

  const validateJson = (value: string) => {
    if (!value.trim()) {
      setJsonError(null)
      return true
    }
    
    try {
      JSON.parse(value)
      setJsonError(null)
      return true
    } catch (error) {
      setJsonError(error instanceof Error ? error.message : 'Invalid JSON')
      return false
    }
  }

  const handleValueChange = (value: string) => {
    setFormData(prev => ({ ...prev, context_value: value }))
    validateJson(value)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!memory || !formData.context_key.trim()) {
      return
    }

    // Validate JSON
    let parsedValue: any
    try {
      // If empty, use empty string
      if (!formData.context_value.trim()) {
        parsedValue = ""
      } else {
        parsedValue = JSON.parse(formData.context_value)
      }
    } catch (error) {
      setJsonError('Invalid JSON format')
      return
    }

    setLoading(true)
    try {
      await onSaveMemory(memory, {
        context_key: formData.context_key.trim(),
        context_value: parsedValue,
        description: formData.description.trim() || undefined
      })

      // Close modal on success
      onOpenChange(false)
    } catch (error) {
      console.error('Failed to update memory:', error)
      // Error handling would be done by the parent component
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    if (memory) {
      // Reset form to original values
      setFormData({
        context_key: memory.context_key,
        context_value: typeof memory.value === 'string' ? memory.value : JSON.stringify(memory.value, null, 2),
        description: memory.description || ''
      })
      setJsonError(null)
    }
    onOpenChange(false)
  }

  // Don't render if no memory is provided
  if (!memory) return null

  const hasChanges = memory && (
    formData.context_key !== memory.context_key ||
    formData.context_value !== (typeof memory.value === 'string' ? memory.value : JSON.stringify(memory.value, null, 2)) ||
    formData.description !== (memory.description || '')
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg bg-card border-border text-card-foreground max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-lg">Edit Memory</DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Update the memory entry details. Changes will be reflected across the system.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Context Key */}
          <div className="space-y-2">
            <Label htmlFor="edit_context_key" className="text-sm font-medium text-foreground">
              Memory Key
            </Label>
            <Input
              id="edit_context_key"
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
            <Label htmlFor="edit_context_value" className="text-sm font-medium text-foreground">
              Value (JSON)
            </Label>
            <Textarea
              id="edit_context_value"
              value={formData.context_value}
              onChange={(e) => handleValueChange(e.target.value)}
              placeholder='{"url": "https://api.example.com", "timeout": 5000}'
              className="bg-background border-border text-foreground font-mono text-sm h-32 resize-none"
              rows={6}
            />
            {jsonError && (
              <div className="text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded px-2 py-1">
                JSON Error: {jsonError}
              </div>
            )}
            <div className="text-xs text-muted-foreground">
              Enter any valid JSON value: string, number, object, array, boolean, or null
            </div>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="edit_description" className="text-sm font-medium text-foreground">
              Description (Optional)
            </Label>
            <Textarea
              id="edit_description"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Brief description of what this memory stores..."
              className="bg-background border-border text-foreground h-20 resize-none"
              rows={3}
            />
          </div>

          {/* Change Indicator */}
          {hasChanges && (
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
              <div className="text-xs text-blue-600 font-medium">
                Changes detected - Click "Save Changes" to apply
              </div>
            </div>
          )}

          <DialogFooter className="gap-2 pt-4">
            <Button 
              type="button" 
              variant="outline" 
              onClick={handleCancel} 
              size="sm"
              disabled={loading}
            >
              <X className="h-3 w-3 mr-2" />
              Cancel
            </Button>
            <Button 
              type="submit" 
              size="sm" 
              disabled={loading || !!jsonError || !formData.context_key.trim() || !hasChanges}
              className="bg-primary hover:bg-primary/90 shadow-lg hover:shadow-primary/25 transition-all"
            >
              {loading ? (
                <>
                  <div className="h-3 w-3 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-3 w-3 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}