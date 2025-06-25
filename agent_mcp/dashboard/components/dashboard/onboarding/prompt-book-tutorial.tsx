"use client"

import React, { useState, useEffect } from 'react'
import { 
  BookOpen, ArrowRight, ArrowLeft, X, Sparkles, Copy, Search, Plus, 
  CheckCircle2, Users, Zap, Target, Lightbulb, Play
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Separator } from '@/components/ui/separator'

interface TutorialStep {
  title: string
  description: string
  content: React.ReactNode
  icon: React.ComponentType<{ className?: string }>
}

const tutorialSteps: TutorialStep[] = [
  {
    title: "Welcome to Prompt Book",
    description: "Your central hub for Agent-MCP workflows and prompts",
    icon: BookOpen,
    content: (
      <div className="space-y-4">
        <div className="text-center space-y-3">
          <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
            <BookOpen className="h-8 w-8 text-primary" />
          </div>
          <h3 className="text-lg font-semibold">Welcome to your Prompt Book!</h3>
          <p className="text-muted-foreground">
            This is your centralized collection of standardized prompts and workflows for Agent-MCP. 
            Think of it as your personal AI prompt library.
          </p>
        </div>
        
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="p-3 border rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-4 w-4 text-primary" />
              <span className="font-medium text-sm">Standardized</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Pre-built prompts for common Agent-MCP tasks
            </p>
          </div>
          <div className="p-3 border rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="font-medium text-sm">Customizable</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Create and edit your own prompt templates
            </p>
          </div>
          <div className="p-3 border rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 mb-2">
              <Copy className="h-4 w-4 text-primary" />
              <span className="font-medium text-sm">Copy & Paste</span>
            </div>
            <p className="text-xs text-muted-foreground">
              One-click copy for instant use in AI assistants
            </p>
          </div>
          <div className="p-3 border rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 mb-2">
              <Users className="h-4 w-4 text-primary" />
              <span className="font-medium text-sm">Team Ready</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Share and collaborate on prompt workflows
            </p>
          </div>
        </div>
      </div>
    )
  },
  {
    title: "Using Existing Prompts",
    description: "Learn how to find and use pre-built prompts",
    icon: Search,
    content: (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Finding the Right Prompt</h3>
        
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-xs font-bold text-primary">1</span>
            </div>
            <div>
              <p className="font-medium">Browse by Category</p>
              <p className="text-sm text-muted-foreground">
                Use the category tabs to find prompts for specific workflows like initialization, task management, or debugging.
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-xs font-bold text-primary">2</span>
            </div>
            <div>
              <p className="font-medium">Search by Keywords</p>
              <p className="text-sm text-muted-foreground">
                Use the search bar to find prompts by title, description, or tags like "admin", "worker", "initialization".
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-xs font-bold text-primary">3</span>
            </div>
            <div>
              <p className="font-medium">Quick Copy or Customize</p>
              <p className="text-sm text-muted-foreground">
                Either copy the template directly or click "Use Template" to customize variables before copying.
              </p>
            </div>
          </div>
        </div>

        <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb className="h-4 w-4 text-blue-600" />
            <span className="font-medium text-blue-900 dark:text-blue-100 text-sm">Pro Tip</span>
          </div>
          <p className="text-xs text-blue-800 dark:text-blue-200">
            Start with the "Quick Start" section to see the essential prompts for getting Agent-MCP running.
          </p>
        </div>
      </div>
    )
  },
  {
    title: "Creating Custom Prompts",
    description: "Build your own reusable prompt templates",
    icon: Plus,
    content: (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Build Your Own Prompts</h3>
        
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-xs font-bold text-primary">1</span>
            </div>
            <div>
              <p className="font-medium">Click "Create Prompt"</p>
              <p className="text-sm text-muted-foreground">
                Use the green button in the top right to start creating a new prompt template.
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-xs font-bold text-primary">2</span>
            </div>
            <div>
              <p className="font-medium">Add Variables with {'{{}}'}</p>
              <p className="text-sm text-muted-foreground">
                Use <code className="bg-muted px-1 rounded">{'{{VARIABLE_NAME}}'}</code> syntax to create dynamic placeholders in your prompts.
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-xs font-bold text-primary">3</span>
            </div>
            <div>
              <p className="font-medium">Auto-Detect Variables</p>
              <p className="text-sm text-muted-foreground">
                Click "Detect Variables" to automatically find and configure all the variables in your template.
              </p>
            </div>
          </div>
        </div>

        <div className="bg-muted/30 border rounded-lg p-3">
          <p className="font-medium text-sm mb-2">Example Template:</p>
          <code className="text-xs bg-background border rounded px-2 py-1 block">
            Create a {'{{AGENT_TYPE}}'} agent with ID "{'{{AGENT_ID}}'}" to {'{{TASK_DESCRIPTION}}'}.
          </code>
          <div className="mt-2 flex flex-wrap gap-1">
            <Badge variant="outline" className="text-xs">AGENT_TYPE</Badge>
            <Badge variant="outline" className="text-xs">AGENT_ID</Badge>
            <Badge variant="outline" className="text-xs">TASK_DESCRIPTION</Badge>
          </div>
        </div>
      </div>
    )
  },
  {
    title: "Prompt Workflows",
    description: "Chain prompts together for complex workflows",
    icon: Zap,
    content: (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Building Agent Workflows</h3>
        
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Agent-MCP works best when you follow a structured workflow. Here's the typical sequence:
          </p>
          
          <div className="space-y-2">
            {[
              { step: 1, title: "Admin Initialization", desc: "Set up your admin agent with the token" },
              { step: 2, title: "Add Project Context", desc: "Load your MCD and project documentation" },
              { step: 3, title: "Create Worker Agents", desc: "Spawn specialized workers for different tasks" },
              { step: 4, title: "Initialize Workers", desc: "Set up each worker with their specific role" },
              { step: 5, title: "Assign Tasks", desc: "Delegate work to the appropriate agents" },
              { step: 6, title: "Monitor & Debug", desc: "Track progress and troubleshoot issues" }
            ].map(({ step, title, desc }) => (
              <div key={step} className="flex items-center gap-3 p-2 border rounded-lg">
                <div className="w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                  {step}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-sm">{title}</p>
                  <p className="text-xs text-muted-foreground">{desc}</p>
                </div>
                <ArrowRight className="h-3 w-3 text-muted-foreground" />
              </div>
            ))}
          </div>
        </div>

        <div className="bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <span className="font-medium text-green-900 dark:text-green-100 text-sm">Best Practice</span>
          </div>
          <p className="text-xs text-green-800 dark:text-green-200">
            Each prompt category corresponds to a different stage in this workflow. Use them in sequence for best results.
          </p>
        </div>
      </div>
    )
  },
  {
    title: "Ready to Start!",
    description: "You're all set to use the Prompt Book effectively",
    icon: Play,
    content: (
      <div className="space-y-4 text-center">
        <div className="mx-auto w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center">
          <CheckCircle2 className="h-8 w-8 text-green-500" />
        </div>
        
        <div>
          <h3 className="text-lg font-semibold">You're Ready to Go!</h3>
          <p className="text-muted-foreground">
            You now know how to use and create prompts in the Prompt Book. Here are some quick actions to get started:
          </p>
        </div>
        
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="p-3 border rounded-lg bg-primary/5 border-primary/20">
            <div className="flex items-center gap-2 mb-1">
              <BookOpen className="h-4 w-4 text-primary" />
              <span className="font-medium text-sm">Try a Quick Start</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Use the admin initialization prompt to set up your first agent
            </p>
          </div>
          <div className="p-3 border rounded-lg bg-primary/5 border-primary/20">
            <div className="flex items-center gap-2 mb-1">
              <Plus className="h-4 w-4 text-primary" />
              <span className="font-medium text-sm">Create Your First</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Build a custom prompt for your specific project needs
            </p>
          </div>
        </div>
        
        <Separator />
        
        <div className="text-xs text-muted-foreground">
          💡 Tip: You can always access this tutorial again from the help menu
        </div>
      </div>
    )
  }
]

interface PromptBookTutorialProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function PromptBookTutorial({ open, onOpenChange }: PromptBookTutorialProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [hasCompletedTutorial, setHasCompletedTutorial] = useState(false)

  useEffect(() => {
    // Check if user has seen the tutorial before
    const completed = localStorage.getItem('prompt-book-tutorial-completed')
    setHasCompletedTutorial(completed === 'true')
  }, [])

  const nextStep = () => {
    if (currentStep < tutorialSteps.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const closeTutorial = () => {
    localStorage.setItem('prompt-book-tutorial-completed', 'true')
    setHasCompletedTutorial(true)
    onOpenChange(false)
    setCurrentStep(0)
  }

  const currentStepData = tutorialSteps[currentStep]
  const isLastStep = currentStep === tutorialSteps.length - 1

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <currentStepData.icon className="h-5 w-5 text-primary" />
              <DialogTitle>{currentStepData.title}</DialogTitle>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={closeTutorial}
              className="h-6 w-6 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <DialogDescription>
            {currentStepData.description}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Progress Indicator */}
          <div className="flex items-center gap-1">
            {tutorialSteps.map((_, index) => (
              <div
                key={index}
                className={`h-2 flex-1 rounded-full transition-all ${
                  index <= currentStep ? 'bg-primary' : 'bg-muted'
                }`}
              />
            ))}
          </div>

          {/* Step Content */}
          <div className="min-h-[300px]">
            {currentStepData.content}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Step {currentStep + 1} of {tutorialSteps.length}
            </div>
            
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={prevStep}
                disabled={currentStep === 0}
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              
              {isLastStep ? (
                <Button
                  size="sm"
                  onClick={closeTutorial}
                  className="bg-primary hover:bg-primary/90"
                >
                  <CheckCircle2 className="h-4 w-4 mr-1" />
                  Get Started
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={nextStep}
                  className="bg-primary hover:bg-primary/90"
                >
                  Next
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// Auto-trigger tutorial for first-time users
export function usePromptBookTutorial() {
  const [showTutorial, setShowTutorial] = useState(false)

  useEffect(() => {
    const hasSeenTutorial = localStorage.getItem('prompt-book-tutorial-completed')
    if (!hasSeenTutorial) {
      // Small delay to let the component mount
      const timer = setTimeout(() => {
        setShowTutorial(true)
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [])

  return { showTutorial, setShowTutorial }
}