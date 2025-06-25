"use client"

import { MainLayout } from "@/components/layout/main-layout"
import { OverviewDashboard } from "@/components/dashboard/overview-dashboard"
import { useDashboard } from "@/lib/store"

// Placeholder components for other views
function AgentsView() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
        <p className="text-muted-foreground">Manage and monitor your agents</p>
      </div>
      <div className="glass-container p-8 text-center">
        <p className="text-muted-foreground">Agent management view coming soon...</p>
      </div>
    </div>
  )
}

function TasksView() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Tasks</h1>
        <p className="text-muted-foreground">Orchestrate and manage tasks</p>
      </div>
      <div className="glass-container p-8 text-center">
        <p className="text-muted-foreground">Task management view coming soon...</p>
      </div>
    </div>
  )
}

function SystemView() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System</h1>
        <p className="text-muted-foreground">Monitor system health and performance</p>
      </div>
      <div className="glass-container p-8 text-center">
        <p className="text-muted-foreground">System monitoring view coming soon...</p>
      </div>
    </div>
  )
}

export default function HomePage() {
  const { currentView } = useDashboard()

  const renderCurrentView = () => {
    switch (currentView) {
      case 'overview':
        return <OverviewDashboard />
      case 'agents':
        return <AgentsView />
      case 'tasks':
        return <TasksView />
      case 'system':
        return <SystemView />
      default:
        return <OverviewDashboard />
    }
  }

  return (
    <MainLayout>
      {renderCurrentView()}
    </MainLayout>
  )
}
