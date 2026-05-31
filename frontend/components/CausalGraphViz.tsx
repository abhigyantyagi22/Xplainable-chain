'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { apiGet } from '@/lib/api';
import {
  ReactFlow,
  Controls,
  Background,
  MarkerType,
  Position,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

interface CausalNode {
  id: string;
  label: string;
  type: string;
}

interface CausalEdge {
  source: string;
  target: string;
  weight: number;
  type: string;
  strength: string;
  label: string;
}

interface CausalGraphData {
  graph: {
    nodes: CausalNode[];
    edges: CausalEdge[];
  };
}

const nodeTypeColors = {
  feature: '#3b82f6',      // blue
  confounder: '#f59e0b',   // orange
  outcome: '#ef4444',      // red
  mediator: '#10b981',     // green
};

export default function CausalGraphViz() {
  const [graphData, setGraphData] = useState<CausalGraphData | null>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCausalGraph();
  }, []);

  const fetchCausalGraph = async () => {
    try {
      const data = await apiGet<CausalGraphData>('/api/causal/graph');
      setGraphData(data);
      layoutGraph(data);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setLoading(false);
    }
  };

  const layoutGraph = (data: CausalGraphData) => {
    const { nodes: graphNodes, edges: graphEdges } = data.graph;

    // Simple hierarchical layout
    const nodesByType: Record<string, CausalNode[]> = {
      confounder: [],
      feature: [],
      mediator: [],
      outcome: [],
    };

    graphNodes.forEach(node => {
      const nodeType = node.type || 'feature';
      if (!nodesByType[nodeType]) {
        nodesByType[nodeType] = [];
      }
      nodesByType[nodeType].push(node);
    });

    const flowNodes: Node[] = [];
    let yPosition = 0;
    const xSpacing = 250;
    const ySpacing = 100;

    // Layout: confounders at top, features in middle-top, mediators in middle-bottom, outcome at bottom
    const layers = ['confounder', 'feature', 'mediator', 'outcome'];

    layers.forEach((layerType) => {
      const layerNodes = nodesByType[layerType] || [];
      const layerWidth = layerNodes.length * xSpacing;
      const startX = -layerWidth / 2;

      layerNodes.forEach((node, index) => {
        flowNodes.push({
          id: node.id,
          type: 'default',
          data: { 
            label: (
              <div className="text-center">
                <div className="font-semibold text-sm">{node.label}</div>
                <div className="text-xs text-gray-500 capitalize">{node.type}</div>
              </div>
            )
          },
          position: { x: startX + index * xSpacing, y: yPosition },
          sourcePosition: Position.Bottom,
          targetPosition: Position.Top,
          style: {
            background: nodeTypeColors[node.type as keyof typeof nodeTypeColors] || nodeTypeColors.feature,
            color: 'white',
            border: '1px solid #222',
            borderRadius: 8,
            padding: 10,
            minWidth: 150,
          },
        });
      });

      if (layerNodes.length > 0) {
        yPosition += ySpacing;
      }
    });

    const flowEdges: Edge[] = graphEdges.map((edge, index) => ({
      id: `edge-${index}`,
      source: edge.source,
      target: edge.target,
      label: `${edge.label} (${edge.strength})`,
      type: 'smoothstep',
      animated: edge.strength === 'strong',
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 20,
        height: 20,
      },
      style: { 
        stroke: edge.strength === 'strong' ? '#2563eb' : edge.strength === 'moderate' ? '#64748b' : '#cbd5e1',
        strokeWidth: edge.strength === 'strong' ? 3 : edge.strength === 'moderate' ? 2 : 1,
      },
      labelStyle: { fontSize: 10, fill: '#64748b', fontWeight: edge.strength === 'strong' ? 'bold' : 'normal' },
      labelBgStyle: { fill: '#ffffff', fillOpacity: 0.9 },
    }));

    setNodes(flowNodes);
    setEdges(flowEdges);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[600px] bg-gray-50 rounded-lg">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading causal graph...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[600px] bg-red-50 rounded-lg">
        <div className="text-center">
          <p className="text-red-600 font-semibold">Error loading causal graph</p>
          <p className="text-gray-600 mt-2">{error}</p>
          <button
            onClick={fetchCausalGraph}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-[600px] bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
      <div className="p-4 bg-white border-b border-gray-200">
        <h2 className="text-xl font-bold text-gray-900">Causal Graph Structure</h2>
        <p className="text-sm text-gray-600 mt-1">
          Directed Acyclic Graph (DAG) showing causal relationships between blockchain features
        </p>
        <div className="flex gap-4 mt-3">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: nodeTypeColors.feature }}></div>
            <span className="text-xs text-gray-700">Features</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: nodeTypeColors.confounder }}></div>
            <span className="text-xs text-gray-700">Confounders</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: nodeTypeColors.mediator }}></div>
            <span className="text-xs text-gray-700">Mediators</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: nodeTypeColors.outcome }}></div>
            <span className="text-xs text-gray-700">Fraud Outcome</span>
          </div>
        </div>
      </div>
      <div className="h-[calc(100%-140px)] relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          attributionPosition="bottom-left"
          style={{ position: 'absolute', inset: 0 }}
          proOptions={{ hideAttribution: true }}
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>
    </div>
  );
}
