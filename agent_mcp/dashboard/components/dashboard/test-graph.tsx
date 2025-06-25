"use client"

import React from 'react'
import ReactFlow, { 
  Node, 
  Edge, 
  Controls, 
  Background,
  BackgroundVariant,
  ReactFlowProvider
} from 'reactflow'
import 'reactflow/dist/style.css'

const initialNodes: Node[] = [
  {
    id: '1',
    type: 'default',
    position: { x: 250, y: 100 },
    data: { label: 'Test Node 1' },
    style: {
      background: '#ff0072',
      color: 'white',
      border: '2px solid #222',
      borderRadius: '8px',
      padding: '10px',
    }
  },
  {
    id: '2',
    type: 'default', 
    position: { x: 100, y: 200 },
    data: { label: 'Test Node 2' },
    style: {
      background: '#0072ff',
      color: 'white',
      border: '2px solid #222',
      borderRadius: '8px',
      padding: '10px',
    }
  },
  {
    id: '3',
    type: 'default',
    position: { x: 400, y: 200 },
    data: { label: 'Test Node 3' },
    style: {
      background: '#00ff72',
      color: 'black',
      border: '2px solid #222',
      borderRadius: '8px',
      padding: '10px',
    }
  }
]

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true },
  { id: 'e1-3', source: '1', target: '3', animated: true }
]

export function TestGraph() {
  return (
    <div style={{ width: '100%', height: '400px', border: '2px solid red' }}>
      <ReactFlowProvider>
        <ReactFlow
          nodes={initialNodes}
          edges={initialEdges}
          fitView
          fitViewOptions={{ padding: 0.2 }}
        >
          <Controls />
          <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  )
}