"use client"

import React, { useState, useEffect } from "react"
import { Plus, Server, Settings, Wifi, WifiOff, AlertCircle, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useServerStore, MCPServer } from "@/lib/stores/server-store"

export function ProjectPicker() {
  const {
    servers,
    activeServerId,
    isConnecting,
    connectionError,
    setActiveServer,
    refreshAllServers,
    disconnectServer
  } = useServerStore()

  const [isOpen, setIsOpen] = useState(false)
  const activeServer = servers.find(s => s.id === activeServerId)

  useEffect(() => {
    // Auto-refresh server status every 30 seconds
    const interval = setInterval(() => {
      refreshAllServers()
    }, 30000)

    return () => clearInterval(interval)
  }, [refreshAllServers])

  const handleServerSelect = async (serverId: string) => {
    await setActiveServer(serverId)
    setIsOpen(false)
  }

  const getStatusIcon = (status: MCPServer['status']) => {
    switch (status) {
      case 'connected':
        return <Wifi className="h-4 w-4 text-green-500" />
      case 'connecting':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return <WifiOff className="h-4 w-4 text-muted-foreground" />
    }
  }

  const getStatusColor = (status: MCPServer['status']) => {
    switch (status) {
      case 'connected':
        return 'bg-green-500'
      case 'connecting':
        return 'bg-blue-500'
      case 'error':
        return 'bg-red-500'
      default:
        return 'bg-muted-foreground'
    }
  }

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="justify-between min-w-[200px]">
          <div className="flex items-center space-x-2">
            {isConnecting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <div className={`w-2 h-2 rounded-full ${activeServer ? getStatusColor(activeServer.status) : 'bg-muted-foreground'}`} />
            )}
            <span className="truncate">
              {activeServer ? activeServer.name : 'Select Project'}
            </span>
          </div>
          <Settings className="h-4 w-4 ml-2 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent className="w-80" align="start">
        <DropdownMenuLabel className="flex items-center justify-between">
          MCP Server Projects
          <Button
            variant="ghost"
            size="sm"
            onClick={() => refreshAllServers()}
            className="h-6 w-6 p-0"
          >
            <Server className="h-3 w-3" />
          </Button>
        </DropdownMenuLabel>
        
        <DropdownMenuSeparator />

        {connectionError && (
          <div className="p-2">
            <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950">
              <CardContent className="p-3">
                <div className="flex items-center space-x-2">
                  <AlertCircle className="h-4 w-4 text-red-500" />
                  <span className="text-sm text-red-700 dark:text-red-300">
                    {connectionError}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        <div className="max-h-[300px] overflow-y-auto">
          {servers.map((server) => (
            <DropdownMenuItem
              key={server.id}
              onClick={() => handleServerSelect(server.id)}
              className="flex items-center justify-between p-3 cursor-pointer"
              disabled={isConnecting}
            >
              <div className="flex items-center space-x-3">
                {getStatusIcon(server.status)}
                <div className="flex flex-col">
                  <span className="font-medium">{server.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {server.host}:{server.port}
                  </span>
                  {server.description && (
                    <span className="text-xs text-muted-foreground">
                      {server.description}
                    </span>
                  )}
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                {server.id === activeServerId && (
                  <Badge variant="secondary" className="text-xs">
                    Active
                  </Badge>
                )}
                <Badge 
                  variant={server.status === 'connected' ? 'default' : 'secondary'}
                  className="text-xs"
                >
                  {server.status}
                </Badge>
              </div>
            </DropdownMenuItem>
          ))}
        </div>

        <DropdownMenuSeparator />
        
        <div className="p-2 space-y-2">
          <AddServerDialog />
          
          {activeServerId && (
            <Button
              variant="outline"
              size="sm"
              onClick={disconnectServer}
              className="w-full"
            >
              Disconnect
            </Button>
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function AddServerDialog() {
  const { addServer } = useServerStore()
  const [isOpen, setIsOpen] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    host: 'localhost',
    port: 8080,
    description: ''
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.name.trim()) return

    addServer({
      name: formData.name.trim(),
      host: formData.host.trim() || 'localhost',
      port: formData.port,
      description: formData.description.trim()
    })

    setFormData({
      name: '',
      host: 'localhost',
      port: 8080,
      description: ''
    })
    
    setIsOpen(false)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="w-full">
          <Plus className="h-4 w-4 mr-2" />
          Add Server
        </Button>
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Add MCP Server</DialogTitle>
          <DialogDescription>
            Add a new MCP server to connect to. This could be a local development server or a remote instance.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="name">Project Name</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              placeholder="My Project"
              required
            />
          </div>
          
          <div className="grid grid-cols-3 gap-2">
            <div className="col-span-2">
              <Label htmlFor="host">Host</Label>
              <Input
                id="host"
                value={formData.host}
                onChange={(e) => setFormData(prev => ({ ...prev, host: e.target.value }))}
                placeholder="localhost"
              />
            </div>
            <div>
              <Label htmlFor="port">Port</Label>
              <Input
                id="port"
                type="number"
                value={formData.port}
                onChange={(e) => setFormData(prev => ({ ...prev, port: parseInt(e.target.value) || 8080 }))}
                placeholder="8080"
              />
            </div>
          </div>
          
          <div className="grid gap-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Input
              id="description"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Brief description of this server"
            />
          </div>
          
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">Add Server</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}