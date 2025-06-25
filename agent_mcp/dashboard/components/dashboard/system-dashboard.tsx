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
      <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b bg-background/95 backdrop-blur">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">System</h1>
          <p className="text-sm sm:text-base text-muted-foreground">
            System architecture and real-time graph visualization
          </p>
        </div>
        <Badge variant="outline" className="status-online text-xs sm:text-sm">
          <Activity className="h-3 w-3 mr-1" />
          <span className="hidden sm:inline">All Systems Operational</span>
          <span className="sm:hidden">Online</span>
        </Badge>
      </div>

      {/* Full Page Graph */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <VisGraph fullscreen />
      </div>
    </div>
  )
}