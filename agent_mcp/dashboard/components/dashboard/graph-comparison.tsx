"use client"

import React from "react"
import { VisGraph } from "./vis-graph-simple"
import { VisGraphImproved } from "./vis-graph-improved"

export function GraphComparison() {
  return (
    <div className="h-full w-full grid grid-cols-2 gap-4 p-4">
      <div className="border border-border rounded-lg overflow-hidden">
        <div className="bg-background/95 backdrop-blur p-3 border-b">
          <h3 className="text-lg font-semibold">Original Layout</h3>
          <p className="text-sm text-muted-foreground">Global crown pattern</p>
        </div>
        <div className="h-[calc(100%-80px)]">
          <VisGraph fullscreen />
        </div>
      </div>
      
      <div className="border border-border rounded-lg overflow-hidden">
        <div className="bg-background/95 backdrop-blur p-3 border-b">
          <h3 className="text-lg font-semibold">Improved Layout</h3>
          <p className="text-sm text-muted-foreground">Cluster-based organization</p>
        </div>
        <div className="h-[calc(100%-80px)]">
          <VisGraphImproved fullscreen />
        </div>
      </div>
    </div>
  )
}