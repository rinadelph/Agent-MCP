"use client"

import { MainLayout } from "@/components/layout/main-layout"
import { OverviewDashboard } from "@/components/dashboard/overview-dashboard"
import { AgentsDashboard } from "@/components/dashboard/agents-dashboard"
import { TasksDashboard } from "@/components/dashboard/tasks-dashboard"
import { useDashboard } from "@/lib/store"

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
        return <AgentsDashboard />
      case 'tasks':
        return <TasksDashboard />
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
