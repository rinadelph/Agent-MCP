"use client"

import React from "react"
import { ThemeToggle } from "./theme-toggle"
import { ProjectPicker } from "@/components/server/project-picker"

export function Header() {

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center justify-between px-[var(--space-fluid-lg)]">
        {/* Project Picker */}
        <ProjectPicker />

        {/* Theme Toggle */}
        <ThemeToggle />
      </div>
    </header>
  )
}