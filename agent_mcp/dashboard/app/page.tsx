"use client"

import { MainLayout } from "@/components/layout/main-layout"
import { OverviewDashboard } from "@/components/dashboard/overview-dashboard"
import { AgentsDashboard } from "@/components/dashboard/agents-dashboard"
import { TasksDashboard } from "@/components/dashboard/tasks-dashboard"
import { SystemDashboard } from "@/components/dashboard/system-dashboard"
import { useDashboard } from "@/lib/store"

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
        return <SystemDashboard />
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
