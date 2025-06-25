"use client"

import React from "react"
import { useServerStore } from "@/lib/stores/server-store"
import { ServerConnection } from "@/components/server/server-connection"

interface DashboardWrapperProps {
  children: React.ReactNode
}

export function DashboardWrapper({ children }: DashboardWrapperProps) {
  const { activeServerId, servers } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  
  // Show server connection if no server is selected or selected server is not connected
  const isConnected = activeServerId && activeServer?.status === 'connected'
  
  if (!isConnected) {
    return <ServerConnection />
  }
  
  return <div className="h-full w-full">{children}</div>
}