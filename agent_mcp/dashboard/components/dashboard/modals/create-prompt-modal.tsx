"use client"

import React, { useState } from 'react'
import { Plus, Sparkles, Tag, Type, Hash, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { promptCategories, type PromptTemplate } from '@/lib/prompt-book'

interface CreatePromptData {
  title: string
  description: string
  category: string
  template: string
  usage: string
  variables: Array<{
    name: string
    description: string
    placeholder: string
    required: boolean
  }>
  tags: string[]
}

interface CreatePromptModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreatePrompt: (data: CreatePromptData) => void
}

export function CreatePromptModal({ open, onOpenChange, onCreatePrompt }: CreatePromptModalProps) {
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState<CreatePromptData>({
    title: '',
    description: '',
    category: 'coordination',
    template: '',
    usage: '',
    variables: [],
    tags: []
  })
  const [newVariable, setNewVariable] = useState({
    name: '',
    description: '',
    placeholder: '',
    required: false
  })
  const [newTag, setNewTag] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.title.trim() || !formData.template.trim()) {
      return
    }

    setLoading(true)
    try {
      onCreatePrompt(formData)

      // Reset form and close modal
      setFormData({
        title: '',
        description: '',
        category: 'coordination',
        template: '',
        usage: '',
        variables: [],
        tags: []
      })
      onOpenChange(false)
    } catch (error) {
      console.error('Failed to create prompt:', error)
    } finally {
      setLoading(false)
    }
  }

  const addVariable = () => {
    if (newVariable.name.trim()) {
      setFormData(prev => ({
        ...prev,
        variables: [...prev.variables, { ...newVariable }]
      }))
      setNewVariable({
        name: '',
        description: '',
        placeholder: '',
        required: false
      })
    }
  }

  const removeVariable = (index: number) => {
    setFormData(prev => ({
      ...prev,
      variables: prev.variables.filter((_, i) => i !== index)
    }))
  }

  const addTag = () => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, newTag.trim()]
      }))
      setNewTag('')
    }
  }

  const removeTag = (tag: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tag)
    }))
  }

  const detectVariables = () => {
    const template = formData.template
    const variableMatches = template.match(/{{([^}]+)}}/g)
    
    if (variableMatches) {
      const detectedVars = variableMatches
        .map(match => match.slice(2, -2))
        .filter(varName => !formData.variables.some(v => v.name === varName))
        .map(varName => ({
          name: varName,
          description: `Description for ${varName}`,
          placeholder: `Enter ${varName.toLowerCase()}`,
          required: true
        }))

      setFormData(prev => ({
        ...prev,
        variables: [...prev.variables, ...detectedVars]
      }))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-card border-border text-card-foreground">
        <DialogHeader>
          <DialogTitle className="text-lg flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Create Custom Prompt
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Create your own reusable prompt template for Agent-MCP workflows
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-foreground">Basic Information</h3>
            
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="title" className="text-sm font-medium text-foreground">
                  Title <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="title"
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="e.g., Create API Worker Agent"
                  className="bg-background border-border text-foreground"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="category" className="text-sm font-medium text-foreground">
                  Category
                </Label>
                <Select value={formData.category} onValueChange={(value) => setFormData(prev => ({ ...prev, category: value }))}>
                  <SelectTrigger className="bg-background border-border text-foreground">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {promptCategories.map(category => (
                      <SelectItem key={category.id} value={category.id}>
                        {category.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description" className="text-sm font-medium text-foreground">
                Description
              </Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Brief description of what this prompt does..."
                className="bg-background border-border text-foreground h-20"
                rows={3}
              />
            </div>
          </div>

          {/* Template */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-foreground">Prompt Template</h3>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={detectVariables}
                className="text-xs"
              >
                <Hash className="h-3 w-3 mr-1" />
                Detect Variables
              </Button>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="template" className="text-sm font-medium text-foreground">
                Template <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="template"
                value={formData.template}
                onChange={(e) => setFormData(prev => ({ ...prev, template: e.target.value }))}
                placeholder="Create a worker agent with ID {{AGENT_ID}} to {{TASK_DESCRIPTION}}..."
                className="bg-background border-border text-foreground font-mono text-sm h-32"
                rows={6}
                required
              />
              <div className="text-xs text-muted-foreground">
                Use <code className="bg-muted px-1 rounded">{'{{VARIABLE_NAME}}'}</code> syntax for dynamic variables
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="usage" className="text-sm font-medium text-foreground">
                Usage Instructions
              </Label>
              <Textarea
                id="usage"
                value={formData.usage}
                onChange={(e) => setFormData(prev => ({ ...prev, usage: e.target.value }))}
                placeholder="Explain when and how to use this prompt..."
                className="bg-background border-border text-foreground h-20"
                rows={3}
              />
            </div>
          </div>

          {/* Variables */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-foreground">Variables</h3>
            
            {formData.variables.length > 0 && (
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {formData.variables.map((variable, index) => (
                  <div key={index} className="flex items-center gap-2 p-2 bg-muted/30 rounded-lg">
                    <div className="flex-1 text-sm">
                      <span className="font-mono text-primary">{variable.name}</span>
                      {variable.required && <span className="text-destructive ml-1">*</span>}
                      {variable.description && (
                        <span className="text-muted-foreground ml-2">- {variable.description}</span>
                      )}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeVariable(index)}
                      className="h-6 w-6 p-0 text-destructive hover:text-destructive/80"
                    >
                      ×
                    </Button>
                  </div>
                ))}
              </div>
            )}

            <div className="grid gap-2 sm:grid-cols-3">
              <Input
                value={newVariable.name}
                onChange={(e) => setNewVariable(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Variable name"
                className="font-mono text-sm"
              />
              <Input
                value={newVariable.description}
                onChange={(e) => setNewVariable(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Description"
                className="text-sm"
              />
              <div className="flex gap-1">
                <Input
                  value={newVariable.placeholder}
                  onChange={(e) => setNewVariable(prev => ({ ...prev, placeholder: e.target.value }))}
                  placeholder="Placeholder"
                  className="text-sm flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addVariable}
                  className="px-2"
                >
                  <Plus className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>

          {/* Tags */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-foreground">Tags</h3>
            
            {formData.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-2">
                {formData.tags.map(tag => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="text-xs cursor-pointer hover:bg-destructive hover:text-destructive-foreground"
                    onClick={() => removeTag(tag)}
                  >
                    {tag} ×
                  </Badge>
                ))}
              </div>
            )}

            <div className="flex gap-2">
              <Input
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                placeholder="Add tag..."
                className="text-sm flex-1"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addTag}
                className="px-3"
              >
                <Tag className="h-3 w-3" />
              </Button>
            </div>
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
              disabled={loading || !formData.title.trim() || !formData.template.trim()}
              className="bg-primary hover:bg-primary/90 shadow-lg hover:shadow-primary/25 transition-all"
            >
              {loading ? (
                <>
                  <div className="h-3 w-3 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" />
                  Creating...
                </>
              ) : (
                <>
                  <Sparkles className="h-3 w-3 mr-2" />
                  Create Prompt
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}