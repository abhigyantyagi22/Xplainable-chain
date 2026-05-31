#!/usr/bin/env python3
"""
Fix NOTEARS Graph: Reverse edges based on temporal ordering

CRITICAL FIX: NOTEARS learned reverse causality due to lack of temporal constraints.
This script corrects edge directions using domain knowledge and temporal ordering.

Changes:
- malicious → gas_price   becomes   gas_price → malicious
- malicious → gas_used    becomes   gas_used → malicious

Justification:
Transaction features are SET BEFORE fraud determination.
Therefore, features cause fraud outcome, not vice versa.
"""

import pickle
import networkx as nx
from pathlib import Path
import logging
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_graph(path: Path):
    """Load the discovered causal graph"""
    with open(path, 'rb') as f:
        graph = pickle.load(f)
    logger.info(f"Loaded graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    return graph


def fix_reversed_edges(graph: nx.DiGraph) -> nx.DiGraph:
    """
    Reverse edges that violate temporal ordering
    
    Rule: malicious cannot cause transaction features (temporal impossibility)
    Fix: Reverse all edges FROM malicious TO features
    """
    logger.info("\n🔧 Fixing reversed edges...")
    
    corrected_graph = graph.copy()
    
    # Find all edges from 'malicious'
    if 'malicious' in corrected_graph:
        outgoing_edges = list(corrected_graph.out_edges('malicious', data=True))
        
        if outgoing_edges:
            logger.info(f"\nFound {len(outgoing_edges)} reversed edges:")
            
            for source, target, data in outgoing_edges:
                weight = data['weight']
                logger.warning(f"   ❌ {source} → {target} (weight: {weight:+.3f})")
                
                # Remove wrong edge
                corrected_graph.remove_edge(source, target)
                
                # Add correct edge (reversed direction)
                corrected_graph.add_edge(target, source, weight=weight)
                
                logger.info(f"   ✅ {target} → {source} (weight: {weight:+.3f}) [CORRECTED]")
        else:
            logger.info("✅ No reversed edges found")
    else:
        logger.error("❌ 'malicious' node not in graph!")
        return graph
    
    return corrected_graph


def validate_fixed_graph(graph: nx.DiGraph):
    """Validate the corrected graph"""
    logger.info("\n✅ Validating corrected graph...")
    
    # Check DAG property
    is_dag = nx.is_directed_acyclic_graph(graph)
    logger.info(f"   Is DAG (acyclic): {is_dag}")
    
    if not is_dag:
        logger.error("   ❌ Graph has cycles! Fix failed.")
        return False
    
    # Check edges to malicious
    if 'malicious' in graph:
        incoming = list(graph.predecessors('malicious'))
        outgoing = list(graph.successors('malicious'))
        
        logger.info(f"   Edges TO malicious (causes of fraud): {len(incoming)}")
        logger.info(f"   Edges FROM malicious (reversed): {len(outgoing)}")
        
        if incoming:
            logger.info("\n   🎯 Direct causes of fraud:")
            for cause in incoming:
                weight = graph[cause]['malicious']['weight']
                direction = "increases" if weight > 0 else "decreases"
                logger.info(f"      {cause:25s} → malicious (weight: {weight:+.3f}) [{direction} fraud risk]")
        
        if outgoing:
            logger.warning("\n   ⚠️ Still has reversed edges:")
            for target in outgoing:
                weight = graph['malicious'][target]['weight']
                logger.warning(f"      malicious → {target:25s} (weight: {weight:+.3f})")
            return False
    
    logger.info("\n✅ Graph validation PASSED")
    return True


def visualize_corrected_graph(graph: nx.DiGraph, save_path: Path):
    """Visualize the corrected causal graph"""
    logger.info("\n📈 Visualizing corrected causal graph...")
    
    plt.figure(figsize=(16, 12))
    
    # Use hierarchical layout
    try:
        pos = nx.spring_layout(graph, k=2, iterations=50, seed=42)
    except:
        pos = nx.circular_layout(graph)
    
    # Node colors
    node_colors = []
    for node in graph.nodes():
        if node == 'malicious':
            node_colors.append('#ff4444')  # Red for outcome
        elif node in ['gas_price', 'gas_price_deviation']:
            node_colors.append('#4488ff')  # Blue for gas features
        elif node in ['value', 'amount']:
            node_colors.append('#44ff44')  # Green for value features
        else:
            node_colors.append('#ffaa44')  # Orange for other
    
    # Draw nodes
    nx.draw_networkx_nodes(
        graph, pos,
        node_color=node_colors,
        node_size=3000,
        alpha=0.9
    )
    
    # Draw edges with varying thickness
    edges = graph.edges(data=True)
    weights = [abs(data['weight']) for _, _, data in edges]
    max_weight = max(weights) if weights else 1
    
    edge_widths = [5 * abs(data['weight']) / max_weight for _, _, data in edges]
    
    # Color edges by type
    edge_colors = []
    for u, v, data in graph.edges(data=True):
        if v == 'malicious':
            edge_colors.append('#ff4444')  # Red for edges to fraud
        else:
            edge_colors.append('gray')
    
    nx.draw_networkx_edges(
        graph, pos,
        width=edge_widths,
        alpha=0.6,
        edge_color=edge_colors,
        arrows=True,
        arrowsize=20,
        arrowstyle='->'
    )
    
    # Draw labels
    nx.draw_networkx_labels(
        graph, pos,
        font_size=10,
        font_weight='bold'
    )
    
    # Edge labels
    edge_labels = {(u, v): f"{data['weight']:+.2f}" 
                   for u, v, data in graph.edges(data=True)}
    nx.draw_networkx_edge_labels(
        graph, pos,
        edge_labels,
        font_size=8
    )
    
    plt.title(
        "CORRECTED Causal Graph (Temporal Ordering Applied)\n"
        "Blockchain Fraud Detection - Data-Driven + Domain Knowledge",
        fontsize=16,
        fontweight='bold'
    )
    plt.axis('off')
    plt.tight_layout()
    
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    logger.info(f"✅ Corrected graph visualization saved to {save_path}")
    plt.close()


def save_corrected_graph(graph: nx.DiGraph, path: Path):
    """Save the corrected causal graph"""
    logger.info(f"\n💾 Saving corrected graph to {path}...")
    
    with open(path, 'wb') as f:
        pickle.dump(graph, f)
    
    logger.info("✅ Corrected graph saved successfully")


def main():
    """Main workflow"""
    logger.info("="*80)
    logger.info("FIX NOTEARS REVERSED CAUSALITY")
    logger.info("="*80)
    
    # Paths
    original_path = Path('/app/app/ml/causal_graph.pkl')
    corrected_path = Path('/app/app/ml/causal_graph_corrected.pkl')
    viz_path = Path('/app/app/ml/causal_graph_corrected.png')
    
    # Load original
    original_graph = load_graph(original_path)
    
    # Fix reversed edges
    corrected_graph = fix_reversed_edges(original_graph)
    
    # Validate
    is_valid = validate_fixed_graph(corrected_graph)
    
    if not is_valid:
        logger.error("\n❌ Graph correction failed!")
        return
    
    # Visualize
    visualize_corrected_graph(corrected_graph, viz_path)
    
    # Save
    save_corrected_graph(corrected_graph, corrected_path)
    
    # Also overwrite original (backup made)
    backup_path = Path('/app/app/ml/causal_graph_original.pkl')
    logger.info(f"\n💾 Backing up original to {backup_path}")
    original_graph_copy = original_graph.copy()
    with open(backup_path, 'wb') as f:
        pickle.dump(original_graph_copy, f)
    
    logger.info(f"💾 Overwriting {original_path} with corrected graph")
    save_corrected_graph(corrected_graph, original_path)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("✅ CORRECTION COMPLETE")
    logger.info("="*80)
    
    logger.info(f"\n📊 Summary:")
    logger.info(f"   Original edges: {original_graph.number_of_edges()}")
    logger.info(f"   Corrected edges: {corrected_graph.number_of_edges()}")
    logger.info(f"   Causes of fraud: {len(list(corrected_graph.predecessors('malicious')))}")
    logger.info("")
    logger.info("📁 Files:")
    logger.info(f"   Original (backup): {backup_path}")
    logger.info(f"   Corrected: {corrected_path}")
    logger.info(f"   Active (overwritten): {original_path}")
    logger.info(f"   Visualization: {viz_path}")
    logger.info("")
    logger.info("🎯 Next Steps:")
    logger.info("   1. Inspect causal_graph_corrected.png")
    logger.info("   2. Generate counterfactuals with corrected graph")
    logger.info("   3. Test interventions")
    logger.info("   4. Compare SHAP vs Causal explanations")


if __name__ == "__main__":
    main()
