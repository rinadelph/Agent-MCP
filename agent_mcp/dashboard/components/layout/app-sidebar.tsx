"use client"

import * as React from "react"
import { PanelLeftClose, PanelLeftOpen } from "lucide-react"
import { Button } from "@/components/ui/button"
import { 
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
  useSidebar as useSidebarUI
} from "@/components/ui/sidebar"
import { Navigation } from "./navigation"
import { useSidebar } from "@/lib/store"
import { cn } from "@/lib/utils"
import { ServerManagementModal } from "../server/server-management-modal"

export function AppSidebar() {
  // Zustand store (used by Navigation component)
  const { setCollapsed } = useSidebar()

  // SidebarProvider context (controls actual sidebar behaviour)
  const {
    state, // "expanded" | "collapsed"
    toggleSidebar,
    openMobile,
    setOpenMobile,
    isMobile,
  } = useSidebarUI()

  // Keep the Zustand store in sync with the provider state.
  React.useEffect(() => {
    setCollapsed(state === "collapsed")
  }, [state, setCollapsed])

  // Ensure the sheet (mobile) opens when we navigate to mobile view while expanded.
  React.useEffect(() => {
    if (isMobile && state === "expanded") {
      setOpenMobile(true)
    }
  }, [isMobile, state, setOpenMobile])

  const handleToggle = () => {
    toggleSidebar()
    // Zustand store will update via the effect above once state changes.
  }

  const collapsed = state === "collapsed"

  return (
    <Sidebar 
      variant="sidebar" 
      collapsible="icon"
      className={cn(
        "flex flex-col h-screen z-40 transition-all duration-300",
        collapsed && !isMobile ? "w-16" : "w-64"
      )}
    >
      {/* Sidebar Header */}
      <SidebarHeader className="border-b px-3 py-3">
        <div className="flex items-center justify-between">
          {(!collapsed || isMobile) && (
            <div className="flex items-center space-x-2">
              <div className="h-6 w-6 rounded bg-primary/20 flex items-center justify-center">
                <span className="text-xs font-semibold text-primary">M</span>
              </div>
              <span className="font-semibold text-sm text-foreground">MCP Control</span>
            </div>
          )}
          {!isMobile && (
            <Button
              variant="ghost"
              size="icon"
              onClick={handleToggle}
              className="h-8 w-8 shrink-0"
            >
              {collapsed ? (
                <PanelLeftOpen className="h-4 w-4" />
              ) : (
                <PanelLeftClose className="h-4 w-4" />
              )}
              <span className="sr-only">Toggle sidebar</span>
            </Button>
          )}
        </div>
      </SidebarHeader>

      {/* Sidebar Content */}
      <SidebarContent className="px-0">
        <Navigation />
      </SidebarContent>

      {/* Sidebar Footer */}
      <SidebarFooter className="border-t p-3">
        {!collapsed && (
          <div className="text-xs text-muted-foreground text-center">
            <div className="font-medium text-foreground">AgentMCP Dashboard</div>
            <div className="text-muted-foreground">v2.2 • Improved Dashboard</div>
          </div>
        )}
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}