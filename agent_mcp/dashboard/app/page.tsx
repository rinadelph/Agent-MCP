"use client"

import { MainLayout } from "@/components/layout/main-layout"
import { DashboardWrapper } from "@/components/dashboard/dashboard-wrapper"
import { OverviewDashboard } from "@/components/dashboard/overview-dashboard"
import { AgentsDashboard } from "@/components/dashboard/agents-dashboard"
import { TasksDashboard } from "@/components/dashboard/tasks-dashboard"
import { MemoriesDashboard } from "@/components/dashboard/memories-dashboard"
import { PromptBookDashboard } from "@/components/dashboard/prompt-book-dashboard"
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
      case 'memories':
        return <MemoriesDashboard />
      case 'prompts':
        return <PromptBookDashboard />
      case 'system':
        return <SystemDashboard />
      default:
        return <OverviewDashboard />
    }
  }

  return (
    <MainLayout>
      <DashboardWrapper>
        {renderCurrentView()}
      </DashboardWrapper>
    </MainLayout>
  )
}
