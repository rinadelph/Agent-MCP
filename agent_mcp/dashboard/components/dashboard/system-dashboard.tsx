"use client"

import React from "react"
import { VisGraph } from "./vis-graph-simple"
import { Badge } from "@/components/ui/badge"
import { Activity } from 'lucide-react'

// Main System Dashboard
export function SystemDashboard() {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-[var(--space-fluid-lg)] py-[var(--space-fluid-md)] border-b bg-background/95 backdrop-blur">
        <div>
          <h1 className="text-fluid-3xl font-bold tracking-tight">System</h1>
          <p className="text-fluid-base text-muted-foreground mt-1">
            System architecture and real-time graph visualization
          </p>
        </div>
        <Badge variant="outline" className="status-online text-fluid-sm">
          <Activity className="h-3 w-3 mr-1 md:h-4 md:w-4" />
          <span className="hidden sm:inline">All Systems Operational</span>
          <span className="sm:hidden">Online</span>
        </Badge>
      </div>

      {/* Full Page Graph */}
      <div className="flex-1 min-h-0 overflow-hidden graph-container">
        <VisGraph fullscreen />
      </div>
    </div>
  )
}