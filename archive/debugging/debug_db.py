#!/usr/bin/env python3
"""
Database Structure Debug - What's actually in the file?
"""
import pickle
from pathlib import Path

def main():
    print("DATABASE STRUCTURE DEBUG")
    print("=" * 30)
    
    db_path = Path('/Users/brock/Documents/GitHub/survey-dag-extractor/surveys_db/current_database.pkl')
    
    with open(db_path, 'rb') as f:
        data = pickle.load(f)
    
    print(f"🔍 Database type: {type(data)}")
    
    if hasattr(data, '__dict__'):
        print(f"🔍 Attributes: {list(data.__dict__.keys())}")
    
    if isinstance(data, dict):
        print(f"🔍 Dict keys: {list(data.keys())}")
        
        # Look for NetworkX graph
        for key, value in data.items():
            print(f"   {key}: {type(value)}")
            if hasattr(value, 'number_of_nodes'):
                print(f"     → This is the graph! {value.number_of_nodes()} nodes")
    
    # Try to find the graph in common locations
    possible_graphs = []
    
    if hasattr(data, 'graph'):
        possible_graphs.append(('data.graph', data.graph))
    
    if isinstance(data, dict):
        if 'graph' in data:
            possible_graphs.append(("data['graph']", data['graph']))
        if 'nodes' in data:
            possible_graphs.append(("data['nodes']", data['nodes']))
    
    print(f"\n🔍 Possible graphs found:")
    for name, obj in possible_graphs:
        print(f"   {name}: {type(obj)}")
        if hasattr(obj, 'number_of_nodes'):
            print(f"     → NetworkX graph: {obj.number_of_nodes()} nodes, {obj.number_of_edges()} edges")

if __name__ == "__main__":
    main()
