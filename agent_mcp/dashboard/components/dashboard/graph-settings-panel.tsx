"use client"

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Settings, Save, RotateCcw, X } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface GraphSettings {
  physics: {
    gravitationalConstant: number
    centralGravity: number
    springLength: number
    springConstant: number
    damping: number
    avoidOverlap: number
  }
  crown: {
    adminContextRadius: number
    contextMass: number
    barrierMass: number
    clusterMinRadius: number
  }
  layout: {
    clusterSpacing: number
    contextRadius: number
    taskRadius: number
    fileRadius: number
  }
}

const DEFAULT_SETTINGS: GraphSettings = {
  physics: {
    gravitationalConstant: -10000,
    centralGravity: 0.02,
    springLength: 250,
    springConstant: 0.015,
    damping: 0.3,
    avoidOverlap: 0.9
  },
  crown: {
    adminContextRadius: 400,
    contextMass: 50,
    barrierMass: 75,
    clusterMinRadius: 250
  },
  layout: {
    clusterSpacing: 120,
    contextRadius: 200,
    taskRadius: 350,
    fileRadius: 150
  }
}

interface GraphSettingsPanelProps {
  onSettingsChange: (settings: GraphSettings) => void
  isOpen: boolean
  onClose: () => void
}

export function GraphSettingsPanel({ onSettingsChange, isOpen, onClose }: GraphSettingsPanelProps) {
  const [settings, setSettings] = useState<GraphSettings>(DEFAULT_SETTINGS)
  const [hasChanges, setHasChanges] = useState(false)

  // Load saved settings on mount
  useEffect(() => {
    const saved = localStorage.getItem('graphSettings')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        setSettings(parsed)
        onSettingsChange(parsed)
      } catch (e) {
        console.error('Failed to load saved settings:', e)
      }
    }
  }, [])

  const updateSetting = (category: keyof GraphSettings, key: string, value: number) => {
    const newSettings = {
      ...settings,
      [category]: {
        ...settings[category],
        [key]: value
      }
    }
    setSettings(newSettings)
    setHasChanges(true)
    onSettingsChange(newSettings)
  }

  const saveSettings = () => {
    localStorage.setItem('graphSettings', JSON.stringify(settings))
    setHasChanges(false)
  }

  const resetSettings = () => {
    setSettings(DEFAULT_SETTINGS)
    onSettingsChange(DEFAULT_SETTINGS)
    setHasChanges(true)
  }

  return (
    <div className={cn(
      "fixed right-0 top-0 h-full w-96 bg-background border-l transform transition-transform z-50",
      isOpen ? "translate-x-0" : "translate-x-full"
    )}>
      <Card className="h-full rounded-none border-0">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Graph Settings
            </CardTitle>
            <CardDescription className="text-xs mt-1">
              Adjust physics and layout parameters
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        
        <CardContent className="space-y-6 overflow-y-auto h-[calc(100%-140px)]">
          {/* Physics Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Physics Engine</h3>
            
            <div className="space-y-3">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">Repulsion Force</Label>
                  <span className="text-xs text-muted-foreground">
                    {Math.abs(settings.physics.gravitationalConstant)}
                  </span>
                </div>
                <Slider
                  value={[Math.abs(settings.physics.gravitationalConstant)]}
                  onValueChange={([value]) => updateSetting('physics', 'gravitationalConstant', -value)}
                  min={1000}
                  max={20000}
                  step={500}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">Central Gravity</Label>
                  <span className="text-xs text-muted-foreground">
                    {settings.physics.centralGravity.toFixed(3)}
                  </span>
                </div>
                <Slider
                  value={[settings.physics.centralGravity * 1000]}
                  onValueChange={([value]) => updateSetting('physics', 'centralGravity', value / 1000)}
                  min={0}
                  max={100}
                  step={5}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">Spring Length</Label>
                  <span className="text-xs text-muted-foreground">{settings.physics.springLength}</span>
                </div>
                <Slider
                  value={[settings.physics.springLength]}
                  onValueChange={([value]) => updateSetting('physics', 'springLength', value)}
                  min={100}
                  max={500}
                  step={10}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">Spring Constant</Label>
                  <span className="text-xs text-muted-foreground">
                    {settings.physics.springConstant.toFixed(3)}
                  </span>
                </div>
                <Slider
                  value={[settings.physics.springConstant * 1000]}
                  onValueChange={([value]) => updateSetting('physics', 'springConstant', value / 1000)}
                  min={5}
                  max={50}
                  step={5}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">Damping</Label>
                  <span className="text-xs text-muted-foreground">
                    {settings.physics.damping.toFixed(2)}
                  </span>
                </div>
                <Slider
                  value={[settings.physics.damping * 100]}
                  onValueChange={([value]) => updateSetting('physics', 'damping', value / 100)}
                  min={10}
                  max={90}
                  step={5}
                  className="w-full"
                />
              </div>
            </div>
          </div>

          <Separator />

          {/* Admin Crown Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Admin Context Crown</h3>
            
            <div className="space-y-3">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">Crown Radius</Label>
                  <span className="text-xs text-muted-foreground">{settings.crown.adminContextRadius}</span>
                </div>
                <Slider
                  value={[settings.crown.adminContextRadius]}
                  onValueChange={([value]) => updateSetting('crown', 'adminContextRadius', value)}
                  min={200}
                  max={600}
                  step={20}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">Context Node Mass</Label>
                  <span className="text-xs text-muted-foreground">{settings.crown.contextMass}</span>
                </div>
                <Slider
                  value={[settings.crown.contextMass]}
                  onValueChange={([value]) => updateSetting('crown', 'contextMass', value)}
                  min={10}
                  max={100}
                  step={5}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">Barrier Mass</Label>
                  <span className="text-xs text-muted-foreground">{settings.crown.barrierMass}</span>
                </div>
                <Slider
                  value={[settings.crown.barrierMass]}
                  onValueChange={([value]) => updateSetting('crown', 'barrierMass', value)}
                  min={10}
                  max={150}
                  step={5}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">Cluster Min Distance</Label>
                  <span className="text-xs text-muted-foreground">{settings.crown.clusterMinRadius}</span>
                </div>
                <Slider
                  value={[settings.crown.clusterMinRadius]}
                  onValueChange={([value]) => updateSetting('crown', 'clusterMinRadius', value)}
                  min={100}
                  max={500}
                  step={25}
                  className="w-full"
                />
              </div>
            </div>
          </div>

          <Separator />

          {/* Layout Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Cluster Layout</h3>
            
            <div className="space-y-3">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">Cluster Spacing</Label>
                  <span className="text-xs text-muted-foreground">{settings.layout.clusterSpacing}</span>
                </div>
                <Slider
                  value={[settings.layout.clusterSpacing]}
                  onValueChange={([value]) => updateSetting('layout', 'clusterSpacing', value)}
                  min={50}
                  max={200}
                  step={10}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">Context Ring Radius</Label>
                  <span className="text-xs text-muted-foreground">{settings.layout.contextRadius}</span>
                </div>
                <Slider
                  value={[settings.layout.contextRadius]}
                  onValueChange={([value]) => updateSetting('layout', 'contextRadius', value)}
                  min={100}
                  max={300}
                  step={10}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">Task Ring Radius</Label>
                  <span className="text-xs text-muted-foreground">{settings.layout.taskRadius}</span>
                </div>
                <Slider
                  value={[settings.layout.taskRadius]}
                  onValueChange={([value]) => updateSetting('layout', 'taskRadius', value)}
                  min={200}
                  max={500}
                  step={10}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">File Ring Radius</Label>
                  <span className="text-xs text-muted-foreground">{settings.layout.fileRadius}</span>
                </div>
                <Slider
                  value={[settings.layout.fileRadius]}
                  onValueChange={([value]) => updateSetting('layout', 'fileRadius', value)}
                  min={100}
                  max={300}
                  step={10}
                  className="w-full"
                />
              </div>
            </div>
          </div>
        </CardContent>

        {/* Action Buttons */}
        <div className="absolute bottom-0 left-0 right-0 p-4 bg-background border-t space-y-2">
          <div className="flex gap-2">
            <Button
              onClick={saveSettings}
              disabled={!hasChanges}
              className="flex-1"
              size="sm"
            >
              <Save className="h-4 w-4 mr-2" />
              Save Settings
            </Button>
            <Button
              onClick={resetSettings}
              variant="outline"
              size="sm"
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          </div>
          {hasChanges && (
            <p className="text-xs text-muted-foreground text-center">
              Unsaved changes
            </p>
          )}
        </div>
      </Card>
    </div>
  )
}