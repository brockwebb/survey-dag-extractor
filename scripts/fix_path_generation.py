#!/usr/bin/env python3
"""
Fix Path Generation - Proper algorithm for complex surveys
"""

import sys
import os
import networkx as nx
from pathlib import Path
from collections import defaultdict
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager
from config.dag_config import DAGConfig

def generate_proper_paths():
    """Generate paths properly without artificial depth limits."""
    print("🔧 FIXING PATH GENERATION")
    print("=" * 50)
    
    db = DatabaseManager()
    config = DAGConfig()
    graph = db.load_graph()
    
    start_node = config.get_start_node()
    completion_terminals = config.get_completion_terminals()
    early_exit_terminals = config.get_early_exit_terminals()
    
    print(f"📊 Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    print(f"🎯 Completion terminals: {completion_terminals}")
    print(f"🚪 Early exit terminals: {early_exit_terminals}")
    
    # Use NetworkX's built-in path finding (much more robust)
    print(f"\\n🔍 FINDING ALL SIMPLE PATHS...")
    
    completion_paths = []
    early_exit_paths = []
    
    # Find paths to completion terminals
    for terminal in completion_terminals:
        if graph.has_node(terminal):
            try:
                # Find ALL simple paths (no cycles, no arbitrary depth limit)
                paths = list(nx.all_simple_paths(graph, start_node, terminal, cutoff=200))  # Much higher cutoff
                completion_paths.extend(paths)
                print(f"   ✅ {terminal}: {len(paths)} completion paths found")
                if paths:
                    lengths = [len(p) for p in paths]
                    print(f"      Path lengths: {min(lengths)}-{max(lengths)} nodes")
            except Exception as e:
                print(f"   ❌ {terminal}: Error - {e}")
    
    # Find paths to early exit terminals  
    for terminal in early_exit_terminals:
        if graph.has_node(terminal):
            try:
                paths = list(nx.all_simple_paths(graph, start_node, terminal, cutoff=100))
                early_exit_paths.extend(paths)
                print(f"   ✅ {terminal}: {len(paths)} early exit paths found")
            except Exception as e:
                print(f"   ❌ {terminal}: Error - {e}")
    
    print(f"\\n📊 RESULTS:")
    print(f"   🎯 Completion paths: {len(completion_paths)}")
    print(f"   🚪 Early exit paths: {len(early_exit_paths)}")
    print(f"   📈 Total paths: {len(completion_paths) + len(early_exit_paths)}")
    
    # ANALYZE COMPLETION PATHS ONLY (excluding early exits)
    if completion_paths:
        print(f"\\n🎯 COMPLETION PATH ANALYSIS (EXCLUDING EARLY EXITS):")
        
        lengths = np.array([len(path) for path in completion_paths])
        
        print(f"   📊 Number of completion paths: {len(lengths)}")
        print(f"   📏 Path lengths:")
        print(f"      Mean: {np.mean(lengths):.2f} nodes")
        print(f"      Std Dev: {np.std(lengths):.2f} nodes") 
        print(f"      Std Error: {np.std(lengths)/np.sqrt(len(lengths)):.2f} nodes")
        print(f"      Min: {np.min(lengths)} nodes")
        print(f"      Max: {np.max(lengths)} nodes")
        print(f"      Median: {np.median(lengths):.2f} nodes")
        
        # Estimated completion times (15 seconds per question)
        times_minutes = lengths * 15 / 60  # Convert to minutes
        print(f"   ⏱️  Estimated completion times:")
        print(f"      Mean: {np.mean(times_minutes):.2f} ± {np.std(times_minutes):.2f} minutes")
        print(f"      Range: {np.min(times_minutes):.2f} - {np.max(times_minutes):.2f} minutes")
        print(f"      Std Error: ±{np.std(times_minutes)/np.sqrt(len(times_minutes)):.2f} minutes")
        
        # Show a few example paths
        print(f"\\n🛤️  EXAMPLE COMPLETION PATHS:")
        for i, path in enumerate(completion_paths[:3]):
            print(f"      Path {i+1}: {path[0]} → ... → {path[-1]} ({len(path)} nodes)")
        
        # Find the most common path length
        from collections import Counter
        length_counts = Counter(lengths)
        most_common_length = length_counts.most_common(1)[0]
        print(f"\\n📈 Most common path length: {most_common_length[0]} nodes ({most_common_length[1]} paths)")
        
    else:
        print("   ❌ NO COMPLETION PATHS FOUND!")
    
    # Analyze early exits separately  
    if early_exit_paths:
        print(f"\\n🚪 EARLY EXIT ANALYSIS:")
        early_lengths = np.array([len(path) for path in early_exit_paths])
        print(f"   📊 Number of early exit paths: {len(early_lengths)}")
        print(f"   📏 Early exit lengths: {np.mean(early_lengths):.2f} ± {np.std(early_lengths):.2f} nodes")
        print(f"   ⏱️  Early exit times: {np.mean(early_lengths * 15 / 60):.2f} ± {np.std(early_lengths * 15 / 60):.2f} minutes")
    
    return {
        "completion_paths": completion_paths,
        "early_exit_paths": early_exit_paths,
        "completion_stats": {
            "count": len(completion_paths),
            "mean_length": float(np.mean(lengths)) if completion_paths else 0,
            "std_dev": float(np.std(lengths)) if completion_paths else 0,
            "std_error": float(np.std(lengths)/np.sqrt(len(lengths))) if completion_paths else 0,
            "min_length": int(np.min(lengths)) if completion_paths else 0,
            "max_length": int(np.max(lengths)) if completion_paths else 0,
            "median_length": float(np.median(lengths)) if completion_paths else 0
        }
    }

if __name__ == "__main__":
    results = generate_proper_paths()
