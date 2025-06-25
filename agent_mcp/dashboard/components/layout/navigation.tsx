"use client"

import React from "react"
import { 
  LayoutDashboard, 
  Users, 
  CheckSquare, 
  Monitor, 
  Settings,
  BarChart3,
  Shield,
  Database,
  Zap
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useDashboard, useSidebar } from "@/lib/store"

interface NavItem {
  title: string
  icon: React.ComponentType<{ className?: string }>
  view: 'overview' | 'agents' | 'tasks'
  description?: string
  badge?: string
}

const navigationItems: NavItem[] = [
  {
    title: "Overview",
    icon: LayoutDashboard,
    view: "overview",
    description: "System overview and metrics"
  },
  {
    title: "Agents",
    icon: Users,
    view: "agents",
    description: "Manage and monitor agents"
  },
  {
    title: "Tasks", 
    icon: CheckSquare,
    view: "tasks",
    description: "Task orchestration and management"
  }
]


export function Navigation() {
  const { currentView, setCurrentView } = useDashboard()
  const { isCollapsed } = useSidebar()

  const NavButton = ({ item, isActive = false }: { item: NavItem, isActive?: boolean }) => {
    const button = (
      <Button
        variant={isActive ? "secondary" : "ghost"}
        className={cn(
          "w-full justify-start gap-3 h-11",
          isCollapsed && "justify-center px-2",
          isActive && "bg-secondary text-secondary-foreground font-medium"
        )}
        onClick={() => setCurrentView(item.view)}
      >
        <item.icon className={cn("h-5 w-5", isActive && "text-primary")} />
        {!isCollapsed && (
          <>
            <span className="truncate">{item.title}</span>
            {item.badge && (
              <span className="ml-auto text-xs bg-primary text-primary-foreground px-1.5 py-0.5 rounded-full">
                {item.badge}
              </span>
            )}
          </>
        )}
      </Button>
    )

    if (isCollapsed && item.description) {
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            {button}
          </TooltipTrigger>
          <TooltipContent side="right">
            <p className="font-medium">{item.title}</p>
            <p className="text-sm text-muted-foreground">{item.description}</p>
          </TooltipContent>
        </Tooltip>
      )
    }

    return button
  }

  return (
    <TooltipProvider>
      <nav className="space-y-2 p-3">
        {/* Primary Navigation */}
        <div className="space-y-1">
          {!isCollapsed && (
            <h3 className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Dashboard
            </h3>
          )}
          {navigationItems.map((item) => (
            <NavButton
              key={item.view}
              item={item}
              isActive={currentView === item.view}
            />
          ))}
        </div>


        {/* System Status Indicator */}
        {!isCollapsed && (
          <div className="pt-4">
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50">
              <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs text-muted-foreground">System Online</span>
            </div>
          </div>
        )}
      </nav>
    </TooltipProvider>
  )
}