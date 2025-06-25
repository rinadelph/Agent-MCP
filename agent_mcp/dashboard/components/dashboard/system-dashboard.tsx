"use client"

import React from "react"
import { VisGraph } from "./vis-graph-simple"
import { Badge } from "@/components/ui/badge"
import { Activity } from 'lucide-react'

// Main System Dashboard
export function SystemDashboard() {
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">System</h1>
          <p className="text-muted-foreground">
            System architecture and real-time graph visualization
          </p>
        </div>
        <Badge variant="outline" className="status-online">
          <Activity className="h-3 w-3 mr-1" />
          All Systems Operational
        </Badge>
      </div>

      {/* Full Page Graph */}
      <div className="flex-1">
        <VisGraph fullscreen />
      </div>
    </div>
  )
}