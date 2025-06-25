"use client"

import React, { useState, useEffect } from 'react'
import { Plus, Minus, Type, Hash, ToggleLeft, ToggleRight, Calendar, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'

type ValueType = 'string' | 'number' | 'boolean' | 'array' | 'object' | 'null'

interface SmartValueEditorProps {
  value: any
  onChange: (value: any) => void
  className?: string
}

export function SmartValueEditor({ value, onChange, className }: SmartValueEditorProps) {
  const [valueType, setValueType] = useState<ValueType>('string')
  const [stringValue, setStringValue] = useState('')
  const [numberValue, setNumberValue] = useState(0)
  const [booleanValue, setBooleanValue] = useState(false)
  const [arrayValue, setArrayValue] = useState<any[]>([])
  const [objectValue, setObjectValue] = useState<Record<string, any>>({})

  // Detect and initialize value type
  useEffect(() => {
    if (value === null || value === undefined) {
      setValueType('null')
    } else if (typeof value === 'string') {
      setValueType('string')
      setStringValue(value)
    } else if (typeof value === 'number') {
      setValueType('number')
      setNumberValue(value)
    } else if (typeof value === 'boolean') {
      setValueType('boolean')
      setBooleanValue(value)
    } else if (Array.isArray(value)) {
      setValueType('array')
      setArrayValue(value)
    } else if (typeof value === 'object') {
      setValueType('object')
      setObjectValue(value)
    } else {
      setValueType('string')
      setStringValue(String(value))
    }
  }, [value])

  // Update parent when local state changes
  const updateValue = (newValue: any) => {
    onChange(newValue)
  }

  // Handle type change
  const handleTypeChange = (newType: ValueType) => {
    setValueType(newType)
    
    switch (newType) {
      case 'string':
        const strVal = ''
        setStringValue(strVal)
        updateValue(strVal)
        break
      case 'number':
        const numVal = 0
        setNumberValue(numVal)
        updateValue(numVal)
        break
      case 'boolean':
        const boolVal = false
        setBooleanValue(boolVal)
        updateValue(boolVal)
        break
      case 'array':
        const arrVal: any[] = []
        setArrayValue(arrVal)
        updateValue(arrVal)
        break
      case 'object':
        const objVal: Record<string, any> = {}
        setObjectValue(objVal)
        updateValue(objVal)
        break
      case 'null':
        updateValue(null)
        break
    }
  }

  // Array helpers
  const addArrayItem = () => {
    const newArray = [...arrayValue, '']
    setArrayValue(newArray)
    updateValue(newArray)
  }

  const updateArrayItem = (index: number, newValue: string) => {
    const newArray = [...arrayValue]
    // Try to parse as number if it looks like one
    const parsedValue = !isNaN(Number(newValue)) && newValue !== '' ? Number(newValue) : newValue
    newArray[index] = parsedValue
    setArrayValue(newArray)
    updateValue(newArray)
  }

  const removeArrayItem = (index: number) => {
    const newArray = arrayValue.filter((_, i) => i !== index)
    setArrayValue(newArray)
    updateValue(newArray)
  }

  // Object helpers
  const addObjectKey = () => {
    const newKey = `key${Object.keys(objectValue).length + 1}`
    const newObject = { ...objectValue, [newKey]: '' }
    setObjectValue(newObject)
    updateValue(newObject)
  }

  const updateObjectKey = (oldKey: string, newKey: string) => {
    if (oldKey === newKey) return
    const newObject = { ...objectValue }
    newObject[newKey] = newObject[oldKey]
    delete newObject[oldKey]
    setObjectValue(newObject)
    updateValue(newObject)
  }

  const updateObjectValue = (key: string, newValue: string) => {
    // Try to parse as number if it looks like one
    const parsedValue = !isNaN(Number(newValue)) && newValue !== '' ? Number(newValue) : newValue
    const newObject = { ...objectValue, [key]: parsedValue }
    setObjectValue(newObject)
    updateValue(newObject)
  }

  const removeObjectKey = (key: string) => {
    const newObject = { ...objectValue }
    delete newObject[key]
    setObjectValue(newObject)
    updateValue(newObject)
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Type Selector */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">Data Type</Label>
        <Select value={valueType} onValueChange={handleTypeChange}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="string">
              <div className="flex items-center gap-2">
                <Type className="h-4 w-4" />
                Text (String)
              </div>
            </SelectItem>
            <SelectItem value="number">
              <div className="flex items-center gap-2">
                <Hash className="h-4 w-4" />
                Number
              </div>
            </SelectItem>
            <SelectItem value="boolean">
              <div className="flex items-center gap-2">
                <ToggleLeft className="h-4 w-4" />
                True/False (Boolean)
              </div>
            </SelectItem>
            <SelectItem value="array">
              <div className="flex items-center gap-2">
                <div className="h-4 w-4 border border-current rounded flex items-center justify-center text-xs">[]</div>
                List (Array)
              </div>
            </SelectItem>
            <SelectItem value="object">
              <div className="flex items-center gap-2">
                <div className="h-4 w-4 border border-current rounded flex items-center justify-center text-xs">{'{}'}</div>
                Object
              </div>
            </SelectItem>
            <SelectItem value="null">
              <div className="flex items-center gap-2">
                <div className="h-4 w-4 border border-current rounded bg-muted"></div>
                Null/Empty
              </div>
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Value Editor based on type */}
      <div className="space-y-3">
        {valueType === 'string' && (
          <div className="space-y-2">
            <Label className="text-sm">Text Value</Label>
            <Textarea
              value={stringValue}
              onChange={(e) => {
                setStringValue(e.target.value)
                updateValue(e.target.value)
              }}
              placeholder="Enter text value..."
              className="min-h-[80px]"
            />
          </div>
        )}

        {valueType === 'number' && (
          <div className="space-y-2">
            <Label className="text-sm">Number Value</Label>
            <Input
              type="number"
              value={numberValue}
              onChange={(e) => {
                const val = Number(e.target.value)
                setNumberValue(val)
                updateValue(val)
              }}
              placeholder="Enter number..."
            />
          </div>
        )}

        {valueType === 'boolean' && (
          <div className="space-y-2">
            <Label className="text-sm">Boolean Value</Label>
            <div className="flex items-center gap-3 p-3 border rounded-lg">
              <Switch
                checked={booleanValue}
                onCheckedChange={(checked) => {
                  setBooleanValue(checked)
                  updateValue(checked)
                }}
              />
              <span className="text-sm font-medium">
                {booleanValue ? 'True' : 'False'}
              </span>
              {booleanValue ? (
                <ToggleRight className="h-4 w-4 text-green-600" />
              ) : (
                <ToggleLeft className="h-4 w-4 text-gray-400" />
              )}
            </div>
          </div>
        )}

        {valueType === 'array' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm">Array Items</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addArrayItem}
                className="h-8"
              >
                <Plus className="h-3 w-3 mr-1" />
                Add Item
              </Button>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {arrayValue.map((item, index) => (
                <div key={index} className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs px-2 py-0.5 min-w-[2rem] justify-center">
                    {index}
                  </Badge>
                  <Input
                    value={String(item)}
                    onChange={(e) => updateArrayItem(index, e.target.value)}
                    placeholder={`Item ${index + 1}`}
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => removeArrayItem(index)}
                    className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
              {arrayValue.length === 0 && (
                <div className="text-center py-6 text-muted-foreground text-sm">
                  No items in array. Click "Add Item" to get started.
                </div>
              )}
            </div>
          </div>
        )}

        {valueType === 'object' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm">Object Properties</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addObjectKey}
                className="h-8"
              >
                <Plus className="h-3 w-3 mr-1" />
                Add Property
              </Button>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {Object.entries(objectValue).map(([key, val]) => (
                <div key={key} className="flex items-center gap-2">
                  <Input
                    value={key}
                    onChange={(e) => updateObjectKey(key, e.target.value)}
                    placeholder="Key"
                    className="w-32"
                  />
                  <span className="text-muted-foreground">:</span>
                  <Input
                    value={String(val)}
                    onChange={(e) => updateObjectValue(key, e.target.value)}
                    placeholder="Value"
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => removeObjectKey(key)}
                    className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
              {Object.keys(objectValue).length === 0 && (
                <div className="text-center py-6 text-muted-foreground text-sm">
                  No properties in object. Click "Add Property" to get started.
                </div>
              )}
            </div>
          </div>
        )}

        {valueType === 'null' && (
          <div className="text-center py-6 text-muted-foreground">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-muted mb-2">
              <div className="w-6 h-6 border-2 border-muted-foreground rounded bg-background"></div>
            </div>
            <div className="text-sm">Null/Empty Value</div>
            <div className="text-xs mt-1">This memory will store a null value</div>
          </div>
        )}
      </div>

      {/* Value Preview */}
      <div className="pt-2 border-t">
        <Label className="text-xs text-muted-foreground mb-2 block">JSON Preview:</Label>
        <div className="bg-muted/30 border rounded p-2 font-mono text-xs text-muted-foreground max-h-20 overflow-y-auto">
          {JSON.stringify(
            valueType === 'string' ? stringValue :
            valueType === 'number' ? numberValue :
            valueType === 'boolean' ? booleanValue :
            valueType === 'array' ? arrayValue :
            valueType === 'object' ? objectValue :
            null,
            null,
            2
          )}
        </div>
      </div>
    </div>
  )
}