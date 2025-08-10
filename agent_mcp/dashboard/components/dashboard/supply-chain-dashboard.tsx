"use client"

import React, { useState, useEffect } from "react"
import { RefreshCw, TrendingUp, TrendingDown, AlertTriangle, Package, Truck, DollarSign, Clock, Target, CheckCircle, XCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useServerStore } from "@/lib/stores/server-store"
import { useDataStore } from "@/lib/stores/data-store"

// Supply Chain KPI Data Types
interface SupplyChainKPI {
  id: string
  category: string
  name: string
  value: number
  target?: number
  unit: string
  trend: 'up' | 'down' | 'stable'
  status: 'good' | 'warning' | 'critical'
  description: string
}

interface SupplyChainMetrics {
  timestamp: string
  kpis: SupplyChainKPI[]
  otifRate: number
  inventoryTurnover: number
  forecastAccuracy: number
  perfectOrderRate: number
  totalSupplyChainCost: number
  cashToCashCycle: number
  resilienceIndex: number
  esgScore: number
  leadTimes: {
    procurement: number
    manufacturing: number
    delivery: number
  }
  supplierPerformance: {
    onTimeDelivery: number
    qualityScore: number
    complianceRate: number
  }
}

// Mock data for demonstration
const mockSupplyChainData: SupplyChainMetrics = {
  timestamp: new Date().toISOString(),
  kpis: [
    {
      id: "otif",
      category: "Delivery",
      name: "OTIF Rate",
      value: 94.5,
      target: 95.0,
      unit: "%",
      trend: "up",
      status: "warning",
      description: "On-Time, In-Full delivery performance"
    },
    {
      id: "inventory_turnover",
      category: "Inventory",
      name: "Inventory Turnover",
      value: 8.2,
      target: 10.0,
      unit: "turns/year",
      trend: "up",
      status: "good",
      description: "How efficiently inventory is managed"
    },
    {
      id: "forecast_accuracy",
      category: "Planning",
      name: "Forecast Accuracy",
      value: 87.3,
      target: 90.0,
      unit: "%",
      trend: "stable",
      status: "warning",
      description: "Accuracy of demand forecasting"
    },
    {
      id: "perfect_order",
      category: "Quality",
      name: "Perfect Order Rate",
      value: 92.1,
      target: 95.0,
      unit: "%",
      trend: "down",
      status: "warning",
      description: "Orders delivered without errors"
    },
    {
      id: "supply_chain_cost",
      category: "Financial",
      name: "Total SC Cost",
      value: 12.8,
      target: 12.0,
      unit: "% of sales",
      trend: "down",
      status: "good",
      description: "Total supply chain cost as % of sales"
    },
    {
      id: "cash_cycle",
      category: "Financial",
      name: "Cash-to-Cash Cycle",
      value: 45,
      target: 40,
      unit: "days",
      trend: "down",
      status: "good",
      description: "Time from cash outflow to cash inflow"
    },
    {
      id: "resilience",
      category: "Risk",
      name: "Resilience Index",
      value: 78.5,
      target: 85.0,
      unit: "score",
      trend: "up",
      status: "warning",
      description: "Supply chain resilience and recovery capability"
    },
    {
      id: "esg_score",
      category: "Sustainability",
      name: "ESG Score",
      value: 82.3,
      target: 85.0,
      unit: "score",
      trend: "up",
      status: "good",
      description: "Environmental, Social, and Governance compliance"
    }
  ],
  otifRate: 94.5,
  inventoryTurnover: 8.2,
  forecastAccuracy: 87.3,
  perfectOrderRate: 92.1,
  totalSupplyChainCost: 12.8,
  cashToCashCycle: 45,
  resilienceIndex: 78.5,
  esgScore: 82.3,
  leadTimes: {
    procurement: 12,
    manufacturing: 18,
    delivery: 5
  },
  supplierPerformance: {
    onTimeDelivery: 91.2,
    qualityScore: 95.8,
    complianceRate: 89.4
  }
}

const getTrendIcon = (trend: string) => {
  switch (trend) {
    case 'up':
      return <TrendingUp className="h-4 w-4 text-green-500" />
    case 'down':
      return <TrendingDown className="h-4 w-4 text-red-500" />
    default:
      return <div className="h-4 w-4 rounded-full bg-yellow-500" />
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'good':
      return 'text-green-600 bg-green-100 border-green-200'
    case 'warning':
      return 'text-yellow-600 bg-yellow-100 border-yellow-200'
    case 'critical':
      return 'text-red-600 bg-red-100 border-red-200'
    default:
      return 'text-gray-600 bg-gray-100 border-gray-200'
  }
}

const getCategoryIcon = (category: string) => {
  switch (category) {
    case 'Delivery':
      return <Truck className="h-5 w-5" />
    case 'Inventory':
      return <Package className="h-5 w-5" />
    case 'Financial':
      return <DollarSign className="h-5 w-5" />
    case 'Planning':
      return <Target className="h-5 w-5" />
    case 'Quality':
      return <CheckCircle className="h-5 w-5" />
    case 'Risk':
      return <AlertTriangle className="h-5 w-5" />
    case 'Sustainability':
      return <span className="text-green-600 font-semibold text-sm">ESG</span>
    default:
      return <Clock className="h-5 w-5" />
  }
}

export function SupplyChainDashboard() {
  const { servers, activeServerId } = useServerStore()
  const activeServer = servers.find(s => s.id === activeServerId)
  const { loading, isRefreshing } = useDataStore()
  
  const [supplyChainData, setSupplyChainData] = useState<SupplyChainMetrics>(mockSupplyChainData)
  
  useEffect(() => {
    // In a real implementation, this would fetch from the supply chain API
    // For now, we use mock data
    setSupplyChainData(mockSupplyChainData)
  }, [activeServerId])

  const isConnected = !!activeServerId && activeServer?.status === 'connected'

  if (!isConnected) {
    return (
      <div className="h-full flex items-center justify-center p-4">
        <Card className="max-w-md">
          <CardContent className="flex flex-col items-center justify-center py-12 px-8 text-center">
            <Package className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">Supply Chain Dashboard</h3>
            <p className="text-muted-foreground text-sm">
              Connect to an MCP server to view supply chain metrics and KPIs.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const criticalKPIs = supplyChainData.kpis.filter(kpi => kpi.status === 'critical')
  const warningKPIs = supplyChainData.kpis.filter(kpi => kpi.status === 'warning')

  return (
    <div className="w-full space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Supply Chain Dashboard</h1>
          <p className="text-muted-foreground text-base mt-1">Real-time supply chain KPIs and performance metrics</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="outline" className="text-xs bg-green-500/15 text-green-600 border-green-500/30 font-medium">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse" />
            {activeServer?.name}
          </Badge>
          {supplyChainData?.timestamp && (
            <span className="text-xs text-muted-foreground">
              Last updated: {new Date(supplyChainData.timestamp).toLocaleTimeString()}
            </span>
          )}
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setSupplyChainData({...mockSupplyChainData, timestamp: new Date().toISOString()})}
            disabled={loading || isRefreshing}
            className="text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${(loading || isRefreshing) ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Alert Summary */}
      {(criticalKPIs.length > 0 || warningKPIs.length > 0) && (
        <Card className="border-l-4 border-l-yellow-500">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              <h3 className="font-semibold">Supply Chain Alerts</h3>
            </div>
            <div className="text-sm text-muted-foreground">
              {criticalKPIs.length > 0 && (
                <span className="text-red-600 font-medium">{criticalKPIs.length} critical issues</span>
              )}
              {criticalKPIs.length > 0 && warningKPIs.length > 0 && ', '}
              {warningKPIs.length > 0 && (
                <span className="text-yellow-600 font-medium">{warningKPIs.length} warnings</span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {supplyChainData.kpis.map((kpi) => (
          <Card key={kpi.id} className={`border ${getStatusColor(kpi.status)}`}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getCategoryIcon(kpi.category)}
                  <CardTitle className="text-sm font-medium">{kpi.name}</CardTitle>
                </div>
                {getTrendIcon(kpi.trend)}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="text-2xl font-bold">
                  {kpi.value}{kpi.unit}
                </div>
                {kpi.target && (
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Progress to target</span>
                      <span>{kpi.target}{kpi.unit}</span>
                    </div>
                    <Progress 
                      value={(kpi.value / kpi.target) * 100} 
                      className="h-2"
                    />
                  </div>
                )}
                <p className="text-xs text-muted-foreground">{kpi.description}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Detailed Performance Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Lead Times */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Lead Time Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm">Procurement</span>
                <span className="font-semibold">{supplyChainData.leadTimes.procurement} days</span>
              </div>
              <Progress value={60} className="h-2" />
              
              <div className="flex justify-between items-center">
                <span className="text-sm">Manufacturing</span>
                <span className="font-semibold">{supplyChainData.leadTimes.manufacturing} days</span>
              </div>
              <Progress value={75} className="h-2" />
              
              <div className="flex justify-between items-center">
                <span className="text-sm">Delivery</span>
                <span className="font-semibold">{supplyChainData.leadTimes.delivery} days</span>
              </div>
              <Progress value={40} className="h-2" />
            </div>
          </CardContent>
        </Card>

        {/* Supplier Performance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              Supplier Performance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm">On-Time Delivery</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{supplyChainData.supplierPerformance.onTimeDelivery}%</span>
                  {supplyChainData.supplierPerformance.onTimeDelivery >= 95 ? 
                    <CheckCircle className="h-4 w-4 text-green-500" /> : 
                    <XCircle className="h-4 w-4 text-red-500" />
                  }
                </div>
              </div>
              <Progress value={supplyChainData.supplierPerformance.onTimeDelivery} className="h-2" />
              
              <div className="flex justify-between items-center">
                <span className="text-sm">Quality Score</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{supplyChainData.supplierPerformance.qualityScore}%</span>
                  {supplyChainData.supplierPerformance.qualityScore >= 95 ? 
                    <CheckCircle className="h-4 w-4 text-green-500" /> : 
                    <XCircle className="h-4 w-4 text-red-500" />
                  }
                </div>
              </div>
              <Progress value={supplyChainData.supplierPerformance.qualityScore} className="h-2" />
              
              <div className="flex justify-between items-center">
                <span className="text-sm">Compliance Rate</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{supplyChainData.supplierPerformance.complianceRate}%</span>
                  {supplyChainData.supplierPerformance.complianceRate >= 95 ? 
                    <CheckCircle className="h-4 w-4 text-green-500" /> : 
                    <XCircle className="h-4 w-4 text-red-500" />
                  }
                </div>
              </div>
              <Progress value={supplyChainData.supplierPerformance.complianceRate} className="h-2" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}