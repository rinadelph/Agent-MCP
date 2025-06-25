"use client"

import React, { useState, useMemo, useEffect } from 'react'
import { 
  BookOpen, Search, Copy, CheckCircle2, Filter, Tag, ChevronDown, ChevronRight,
  UserPlus, CheckSquare, Database, Bug, Users, Sparkles, ExternalLink, Plus, HelpCircle, Edit3, X
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Separator } from '@/components/ui/separator'
import { 
  promptCategories, 
  promptTemplates, 
  getPromptsByCategory, 
  searchPrompts, 
  fillPromptTemplate,
  validatePromptVariables,
  type PromptTemplate,
  type PromptCategory
} from '@/lib/prompt-book'
import { CreatePromptModal } from './modals/create-prompt-modal'
import { PromptBookTutorial, usePromptBookTutorial } from './onboarding/prompt-book-tutorial'

// Icon mapping for categories
const categoryIcons = {
  UserPlus,
  CheckSquare,
  Database,
  Bug,
  Users
}

// Component for displaying a single prompt card
const PromptCard = ({ prompt, onSelect, onDelete, isCustom }: { 
  prompt: PromptTemplate; 
  onSelect: (prompt: PromptTemplate) => void;
  onDelete?: (promptId: string) => void;
  isCustom?: boolean;
}) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation()
    await navigator.clipboard.writeText(prompt.template)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (onDelete && isCustom) {
      onDelete(prompt.id)
    }
  }

  return (
    <Card className="cursor-pointer hover:shadow-md transition-all duration-200 group relative">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-lg font-semibold group-hover:text-primary transition-colors">
                {prompt.title}
              </CardTitle>
              {isCustom && (
                <Badge variant="secondary" className="text-xs">
                  Custom
                </Badge>
              )}
            </div>
            <CardDescription className="text-sm text-muted-foreground mt-1">
              {prompt.description}
            </CardDescription>
          </div>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-8 w-8 p-0"
            >
              {copied ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
            {isCustom && onDelete && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDelete}
                className="h-8 w-8 p-0 text-destructive hover:text-destructive/80"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
        
        <div className="flex flex-wrap gap-1 mt-2">
          {prompt.tags.slice(0, 3).map(tag => (
            <Badge key={tag} variant="secondary" className="text-xs">
              {tag}
            </Badge>
          ))}
          {prompt.tags.length > 3 && (
            <Badge variant="outline" className="text-xs">
              +{prompt.tags.length - 3}
            </Badge>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="bg-muted/30 rounded-lg p-3 mb-3">
          <code className="text-xs font-mono text-foreground line-clamp-3">
            {prompt.template.length > 120 
              ? prompt.template.substring(0, 120) + '...' 
              : prompt.template
            }
          </code>
        </div>
        
        <div className="flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            {prompt.variables.length} variable{prompt.variables.length !== 1 ? 's' : ''}
          </div>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => onSelect(prompt)}
            className="text-xs"
          >
            Use Template
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// Component for the prompt builder/editor
const PromptBuilder = ({ prompt, onClose }: {
  prompt: PromptTemplate;
  onClose: () => void;
}) => {
  const [variables, setVariables] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {}
    prompt.variables.forEach(v => {
      initial[v.name] = ''
    })
    return initial
  })
  const [generatedPrompt, setGeneratedPrompt] = useState('')
  const [copied, setCopied] = useState(false)
  const [errors, setErrors] = useState<string[]>([])

  const updateVariable = (name: string, value: string) => {
    setVariables(prev => ({ ...prev, [name]: value }))
  }

  const generatePrompt = () => {
    const validationErrors = validatePromptVariables(prompt, variables)
    setErrors(validationErrors)
    
    if (validationErrors.length === 0) {
      const filled = fillPromptTemplate(prompt.template, variables)
      setGeneratedPrompt(filled)
    }
  }

  const copyPrompt = async () => {
    if (generatedPrompt) {
      await navigator.clipboard.writeText(generatedPrompt)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">{prompt.title}</h3>
        <p className="text-muted-foreground text-sm mb-4">{prompt.description}</p>
        
        <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            <strong>Usage:</strong> {prompt.usage}
          </p>
        </div>
      </div>

      <Separator />

      <div>
        <h4 className="font-medium mb-3">Configure Variables</h4>
        <div className="space-y-4">
          {prompt.variables.map(variable => (
            <div key={variable.name} className="space-y-2">
              <Label htmlFor={variable.name} className="text-sm font-medium">
                {variable.name}
                {variable.required && <span className="text-destructive ml-1">*</span>}
              </Label>
              <Input
                id={variable.name}
                value={variables[variable.name] || ''}
                onChange={(e) => updateVariable(variable.name, e.target.value)}
                placeholder={variable.placeholder}
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">{variable.description}</p>
            </div>
          ))}
        </div>
        
        {errors.length > 0 && (
          <div className="mt-4 space-y-1">
            {errors.map((error, index) => (
              <p key={index} className="text-xs text-destructive">{error}</p>
            ))}
          </div>
        )}
        
        <Button onClick={generatePrompt} className="mt-4 w-full">
          <Sparkles className="h-4 w-4 mr-2" />
          Generate Prompt
        </Button>
      </div>

      {generatedPrompt && (
        <>
          <Separator />
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium">Generated Prompt</h4>
              <Button variant="outline" size="sm" onClick={copyPrompt}>
                {copied ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy
                  </>
                )}
              </Button>
            </div>
            <Textarea
              value={generatedPrompt}
              readOnly
              className="font-mono text-sm h-32 bg-muted/30"
              rows={6}
            />
          </div>
        </>
      )}

      {prompt.examples && prompt.examples.length > 0 && (
        <>
          <Separator />
          <div>
            <h4 className="font-medium mb-3">Examples</h4>
            <div className="space-y-2">
              {prompt.examples.map((example, index) => (
                <div key={index} className="bg-muted/30 rounded-lg p-3">
                  <code className="text-xs font-mono text-foreground whitespace-pre-wrap">
                    {example}
                  </code>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export function PromptBookDashboard() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [selectedPrompt, setSelectedPrompt] = useState<PromptTemplate | null>(null)
  const [builderOpen, setBuilderOpen] = useState(false)
  const [customPrompts, setCustomPrompts] = useState<PromptTemplate[]>([])
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const { showTutorial, setShowTutorial } = usePromptBookTutorial()

  // Load custom prompts from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('custom-prompts')
    if (stored) {
      try {
        setCustomPrompts(JSON.parse(stored))
      } catch (error) {
        console.error('Failed to load custom prompts:', error)
      }
    }
  }, [])

  // Save custom prompts to localStorage when they change
  useEffect(() => {
    localStorage.setItem('custom-prompts', JSON.stringify(customPrompts))
  }, [customPrompts])

  // Filter prompts based on search and category
  const filteredPrompts = useMemo(() => {
    // Combine standard and custom prompts
    let prompts = [...promptTemplates, ...customPrompts]

    if (searchTerm) {
      // Use the search function for standard prompts, then filter custom prompts
      const standardResults = searchPrompts(searchTerm)
      const customResults = customPrompts.filter(p => 
        p.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
      )
      prompts = [...standardResults, ...customResults]
    }

    if (selectedCategory !== 'all') {
      prompts = prompts.filter(p => p.category === selectedCategory)
    }

    return prompts
  }, [searchTerm, selectedCategory, customPrompts])

  // Group prompts by category for display
  const promptsByCategory = useMemo(() => {
    const grouped: Record<string, PromptTemplate[]> = {}
    
    filteredPrompts.forEach(prompt => {
      if (!grouped[prompt.category]) {
        grouped[prompt.category] = []
      }
      grouped[prompt.category].push(prompt)
    })
    
    return grouped
  }, [filteredPrompts])

  const handleSelectPrompt = (prompt: PromptTemplate) => {
    setSelectedPrompt(prompt)
    setBuilderOpen(true)
  }

  const handleCreatePrompt = (promptData: any) => {
    const newPrompt: PromptTemplate = {
      id: `custom-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      title: promptData.title,
      description: promptData.description,
      category: promptData.category,
      template: promptData.template,
      variables: promptData.variables || [],
      usage: promptData.usage || '',
      examples: [],
      tags: promptData.tags || []
    }
    setCustomPrompts(prev => [...prev, newPrompt])
    setCreateModalOpen(false)
  }

  const handleDeleteCustomPrompt = (promptId: string) => {
    setCustomPrompts(prev => prev.filter(p => p.id !== promptId))
  }

  return (
    <div className="w-full space-y-[var(--space-fluid-lg)] -mx-[var(--container-padding)] px-[var(--container-padding)] -my-[var(--space-fluid-lg)] py-[var(--space-fluid-lg)]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-fluid-2xl font-bold text-foreground flex items-center gap-2">
            <BookOpen className="h-8 w-8 text-primary" />
            Prompt Book
          </h1>
          <p className="text-muted-foreground text-fluid-base mt-1">
            Standardized prompts and workflows for Agent-MCP
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {promptTemplates.length + customPrompts.length} prompts
          </Badge>
          <Badge variant="outline" className="text-xs">
            {promptCategories.length} categories
          </Badge>
          {customPrompts.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              {customPrompts.length} custom
            </Badge>
          )}
          <Button
            size="sm"
            onClick={() => setCreateModalOpen(true)}
            className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg hover:shadow-primary/25 transition-all duration-200"
          >
            <Plus className="h-4 w-4 mr-1.5" />
            Create Prompt
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowTutorial(true)}
            className="text-xs"
          >
            <HelpCircle className="h-4 w-4 mr-1.5" />
            Help
          </Button>
        </div>
      </div>

      {/* Search and Filter Controls */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search prompts by title, description, or tags..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={selectedCategory} onValueChange={setSelectedCategory}>
          <SelectTrigger className="w-full sm:w-48">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {promptCategories.map(category => (
              <SelectItem key={category.id} value={category.id}>
                {category.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Quick Start Guide */}
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Quick Start
          </CardTitle>
          <CardDescription>
            Essential prompts to get started with Agent-MCP
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="flex items-center gap-2 text-sm">
              <Badge variant="secondary" className="text-xs">1</Badge>
              <span>Initialize Admin Agent</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Badge variant="secondary" className="text-xs">2</Badge>
              <span>Add Project Context</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Badge variant="secondary" className="text-xs">3</Badge>
              <span>Create Worker Agents</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Badge variant="secondary" className="text-xs">4</Badge>
              <span>Initialize Workers</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Badge variant="secondary" className="text-xs">5</Badge>
              <span>Assign Tasks</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Badge variant="secondary" className="text-xs">6</Badge>
              <span>Monitor & Debug</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Category Tabs */}
      <Tabs value={selectedCategory} onValueChange={setSelectedCategory} className="w-full">
        <TabsList className="grid w-full grid-cols-3 lg:grid-cols-6">
          <TabsTrigger value="all" className="text-xs">All</TabsTrigger>
          {promptCategories.map(category => (
            <TabsTrigger key={category.id} value={category.id} className="text-xs">
              {category.name.split(' ')[0]}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="all" className="mt-6">
          <div className="space-y-6">
            {promptCategories.map(category => {
              const categoryPrompts = promptsByCategory[category.id] || []
              if (categoryPrompts.length === 0) return null

              const IconComponent = categoryIcons[category.icon as keyof typeof categoryIcons] || BookOpen

              return (
                <div key={category.id}>
                  <div className="flex items-center gap-2 mb-4">
                    <IconComponent className="h-5 w-5 text-primary" />
                    <h2 className="text-xl font-semibold">{category.name}</h2>
                    <Badge variant="outline" className="text-xs">
                      {categoryPrompts.length}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground text-sm mb-4">{category.description}</p>
                  
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {categoryPrompts.map(prompt => (
                      <PromptCard
                        key={prompt.id}
                        prompt={prompt}
                        onSelect={handleSelectPrompt}
                        onDelete={handleDeleteCustomPrompt}
                        isCustom={prompt.id.startsWith('custom-')}
                      />
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </TabsContent>

        {promptCategories.map(category => (
          <TabsContent key={category.id} value={category.id} className="mt-6">
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary/10">
                  {React.createElement(categoryIcons[category.icon as keyof typeof categoryIcons] || BookOpen, {
                    className: "h-5 w-5 text-primary"
                  })}
                </div>
                <div>
                  <h2 className="text-xl font-semibold">{category.name}</h2>
                  <p className="text-muted-foreground text-sm">{category.description}</p>
                </div>
              </div>
              
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {(promptsByCategory[category.id] || []).map(prompt => (
                  <PromptCard
                    key={prompt.id}
                    prompt={prompt}
                    onSelect={handleSelectPrompt}
                    onDelete={handleDeleteCustomPrompt}
                    isCustom={prompt.id.startsWith('custom-')}
                  />
                ))}
              </div>
            </div>
          </TabsContent>
        ))}
      </Tabs>

      {/* No Results */}
      {filteredPrompts.length === 0 && (
        <div className="text-center py-12">
          <BookOpen className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">No prompts found</h3>
          <p className="text-muted-foreground text-sm">
            Try adjusting your search terms or category filter
          </p>
        </div>
      )}

      {/* Prompt Builder Dialog */}
      <Dialog open={builderOpen} onOpenChange={setBuilderOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Prompt Builder</DialogTitle>
            <DialogDescription>
              Customize and generate your prompt with the required variables
            </DialogDescription>
          </DialogHeader>
          
          {selectedPrompt && (
            <PromptBuilder
              prompt={selectedPrompt}
              onClose={() => setBuilderOpen(false)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Create Prompt Modal */}
      <CreatePromptModal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        onCreatePrompt={handleCreatePrompt}
      />

      {/* Tutorial */}
      <PromptBookTutorial
        open={showTutorial}
        onOpenChange={setShowTutorial}
      />
    </div>
  )
}