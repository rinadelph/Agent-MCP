"use client"

import React, { useEffect } from "react"
import { Header } from "./header"
import { AppSidebar } from "./app-sidebar"
import { useTheme } from "@/lib/store"
import { cn } from "@/lib/utils"
import { SidebarProvider } from "@/components/ui/sidebar"

interface MainLayoutProps {
  children: React.ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
  const { setTheme, theme } = useTheme()

  // Initialize theme on mount
  useEffect(() => {
    // Set initial theme based on system preference if theme is 'system'
    if (theme === 'system') {
      const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      if (isDark) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    } else {
      if (theme === 'dark') {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    }

    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      if (theme === 'system') {
        setTheme('system') // This will trigger the theme update
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme, setTheme])

  return (
    <SidebarProvider defaultOpen={true}>
      <div className="relative h-screen bg-background flex overflow-hidden w-full">
        {/* Sidebar */}
        <AppSidebar />
        
        {/* Main Content Area */}
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          {/* Header */}
          <Header />
          
          {/* Main Content */}
          <main className="flex-1 overflow-auto min-h-0">
            <div className="fluid-container h-full animate-fade-in">
              {children}
            </div>
          </main>
        </div>
      </div>
    </SidebarProvider>
  )
}

// Add some premium styling for container-fluid
export function PageContainer({ 
  children, 
  className 
}: { 
  children: React.ReactNode
  className?: string 
}) {
  return (
    <div className={cn("space-y-6", className)}>
      {children}
    </div>
  )
}

export function PageHeader({ 
  title, 
  description, 
  children,
  className 
}: { 
  title: string
  description?: string
  children?: React.ReactNode
  className?: string 
}) {
  return (
    <div className={cn("flex items-center justify-between pb-6", className)}>
      <div className="space-y-1">
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        {description && (
          <p className="text-muted-foreground">{description}</p>
        )}
      </div>
      {children && (
        <div className="flex items-center space-x-2">
          {children}
        </div>
      )}
    </div>
  )
}