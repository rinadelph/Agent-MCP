"use client"

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { apiClient } from '@/lib/api'

interface DiagnosticResult {
  test: string
  status: 'success' | 'failed' | 'pending'
  message: string
  details?: any
}

export function CORSDiagnostic() {
  const [results, setResults] = useState<DiagnosticResult[]>([])
  const [isRunning, setIsRunning] = useState(false)

  const addResult = (result: DiagnosticResult) => {
    setResults(prev => [...prev, result])
  }

  const runDiagnostics = async () => {
    setIsRunning(true)
    setResults([])

    // Test 1: Basic fetch to the server
    addResult({
      test: 'Basic Fetch Test',
      status: 'pending',
      message: 'Testing basic connectivity...'
    })

    try {
      const testUrl = 'http://localhost:3000/api/health'
      const response = await fetch(testUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        },
        mode: 'cors'
      })

      if (response.ok) {
        const data = await response.json()
        addResult({
          test: 'Basic Fetch Test',
          status: 'success',
          message: 'Basic fetch successful',
          details: { status: response.status, data }
        })
      } else {
        addResult({
          test: 'Basic Fetch Test',
          status: 'failed',
          message: `HTTP ${response.status}: ${response.statusText}`
        })
      }
    } catch (error) {
      addResult({
        test: 'Basic Fetch Test',
        status: 'failed',
        message: `Failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        details: error
      })
    }

    // Test 2: API Client test
    addResult({
      test: 'API Client Test',
      status: 'pending',
      message: 'Testing API client configuration...'
    })

    try {
      apiClient.setServer('localhost', 3000)
      const corsTest = await apiClient.testCORS()
      
      addResult({
        test: 'API Client Test',
        status: corsTest ? 'success' : 'failed',
        message: corsTest ? 'API client CORS test passed' : 'API client CORS test failed'
      })
    } catch (error) {
      addResult({
        test: 'API Client Test',
        status: 'failed',
        message: `API client test failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        details: error
      })
    }

    // Test 3: Browser information
    addResult({
      test: 'Browser Information',
      status: 'success',
      message: 'Browser details collected',
      details: {
        userAgent: navigator.userAgent,
        isChrome: navigator.userAgent.includes('Chrome'),
        isFirefox: navigator.userAgent.includes('Firefox'),
        origin: window.location.origin,
        protocol: window.location.protocol
      }
    })

    setIsRunning(false)
  }

  const getStatusColor = (status: DiagnosticResult['status']) => {
    switch (status) {
      case 'success': return 'bg-green-500'
      case 'failed': return 'bg-red-500'
      case 'pending': return 'bg-yellow-500'
      default: return 'bg-gray-500'
    }
  }

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle>CORS Diagnostic Tool</CardTitle>
        <CardDescription>
          Diagnose CORS issues between the dashboard and MCP server
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button 
          onClick={runDiagnostics} 
          disabled={isRunning}
          className="w-full"
        >
          {isRunning ? 'Running Diagnostics...' : 'Run CORS Diagnostics'}
        </Button>

        <div className="space-y-3">
          {results.map((result, index) => (
            <div key={index} className="border rounded-lg p-4">
              <div className="flex items-center gap-3 mb-2">
                <Badge className={getStatusColor(result.status)}>
                  {result.status}
                </Badge>
                <h3 className="font-semibold">{result.test}</h3>
              </div>
              
              <p className="text-sm text-gray-600 mb-2">{result.message}</p>
              
              {result.details && (
                <details className="text-xs">
                  <summary className="cursor-pointer text-blue-600 hover:text-blue-800">
                    View Details
                  </summary>
                  <pre className="mt-2 p-2 bg-gray-100 rounded overflow-auto">
                    {JSON.stringify(result.details, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          ))}
        </div>

        {results.length === 0 && !isRunning && (
          <div className="text-center text-gray-500 py-8">
            Click "Run CORS Diagnostics" to start testing
          </div>
        )}
      </CardContent>
    </Card>
  )
}