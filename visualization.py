"""
Visualization Module - Generate interactive HTML visualization
Uses LangExtract's visualization capabilities
"""

import langextract as lx
import json
from pathlib import Path
from typing import Dict, Any

from .config import ExtractorConfig


class DAGVisualizer:
    """
    Generates interactive HTML visualization of the DAG.
    """
    
    def __init__(self, config: ExtractorConfig):
        self.config = config
    
    def generate(self, dag: Dict[str, Any], output_path: Path) -> Path:
        """
        Generate HTML visualization.
        
        Args:
            dag: Complete survey DAG
            output_path: Path for HTML file
            
        Returns:
            Path to generated HTML file
        """
        output_path = Path(output_path)
        
        # Convert DAG to LangExtract format for visualization
        documents = self._convert_to_langextract_format(dag)
        
        # Save as JSONL for LangExtract
        jsonl_path = output_path.with_suffix('.jsonl')
        lx.io.save_annotated_documents(documents, str(jsonl_path))
        
        # Generate HTML visualization
        html_content = lx.visualize(str(jsonl_path))
        
        # Enhance with custom DAG visualization
        enhanced_html = self._enhance_visualization(html_content, dag)
        
        # Save HTML
        with open(output_path, 'w') as f:
            f.write(enhanced_html)
        
        # Clean up JSONL if not debugging
        if not self.config.debug:
            jsonl_path.unlink()
        
        return output_path
    
    def _convert_to_langextract_format(self, dag: Dict) -> list:
        """Convert DAG to LangExtract document format."""
        
        # Create a document for visualization
        survey_info = dag['survey_dag']['metadata']
        graph = dag['survey_dag']['graph']
        
        # Build text representation
        text_parts = []
        text_parts.append(f"Survey: {survey_info['title']}")
        text_parts.append(f"Version: {survey_info['version']}")
        text_parts.append(f"Nodes: {len(graph['nodes'])}")
        text_parts.append(f"Edges: {len(graph['edges'])}")
        text_parts.append("\n--- Survey Flow ---\n")
        
        # Add nodes to text
        for node in graph['nodes']:
            text_parts.append(f"\n{node['id']}: {node['metadata'].get('text', '')[:100]}...")
        
        full_text = "\n".join(text_parts)
        
        # Create extractions for visualization
        extractions = []
        char_offset = 0
        
        # Add nodes as extractions
        for node in graph['nodes']:
            node_text = f"{node['id']}: {node['metadata'].get('text', '')[:50]}"
            start = full_text.find(node_text, char_offset)
            if start >= 0:
                extraction = lx.data.Extraction(
                    extraction_class="node",
                    extraction_text=node['id'],
                    char_start=start,
                    char_end=start + len(node_text),
                    attributes={
                        "type": node['type'],
                        "block": node.get('block', 'main'),
                        "order": node.get('order_index', 0)
                    }
                )
                extractions.append(extraction)
                char_offset = start + len(node_text)
        
        # Create document
        doc = lx.data.Document(
            text=full_text,
            extractions=extractions,
            metadata=survey_info
        )
        
        return [doc]
    
    def _enhance_visualization(self, base_html: str, dag: Dict) -> str:
        """Enhance HTML with custom DAG visualization."""
        
        # Add custom CSS and JavaScript for DAG visualization
        custom_style = """
        <style>
            .dag-summary {
                background: #f5f5f5;
                padding: 20px;
                margin: 20px;
                border-radius: 8px;
            }
            .dag-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .stat-card {
                background: white;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .stat-value {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
            .stat-label {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
            .flow-diagram {
                margin: 20px;
                padding: 20px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .node-flow {
                display: flex;
                align-items: center;
                margin: 10px 0;
            }
            .node-box {
                padding: 8px 12px;
                background: #e3f2fd;
                border: 1px solid #1976d2;
                border-radius: 4px;
                margin: 0 5px;
            }
            .terminal-box {
                background: #ffebee;
                border-color: #d32f2f;
            }
            .arrow {
                color: #666;
                margin: 0 10px;
            }
        </style>
        """
        
        # Build summary section
        graph = dag['survey_dag']['graph']
        stats = dag['survey_dag'].get('analysis', {}).get('statistics', {})
        
        summary_html = f"""
        <div class="dag-summary">
            <h2>Survey DAG Analysis</h2>
            <div class="dag-stats">
                <div class="stat-card">
                    <div class="stat-value">{len(graph['nodes'])}</div>
                    <div class="stat-label">Total Nodes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(graph['edges'])}</div>
                    <div class="stat-label">Total Edges</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(dag['survey_dag']['predicates'])}</div>
                    <div class="stat-label">Predicates</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(graph.get('terminals', []))}</div>
                    <div class="stat-label">Terminal Nodes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats.get('max_depth', 0)}</div>
                    <div class="stat-label">Max Depth</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats.get('complexity_score', 0)}</div>
                    <div class="stat-label">Complexity Score</div>
                </div>
            </div>
        </div>
        """
        
        # Build flow diagram (simplified)
        flow_html = """
        <div class="flow-diagram">
            <h3>Survey Flow Overview</h3>
        """
        
        # Show first few nodes in flow
        start = graph.get('start')
        if start:
            flow_html += f"""
            <div class="node-flow">
                <div class="node-box">{start} (START)</div>
            """
            
            # Find edges from start
            start_edges = [e for e in graph['edges'] if e['source'] == start][:3]
            for edge in start_edges:
                target = edge['target']
                condition = edge['metadata'].get('condition_text', 'always')
                flow_html += f"""
                <span class="arrow">→</span>
                <div class="node-box">{target}<br><small>{condition}</small></div>
                """
            
            flow_html += "</div>"
        
        # Show terminal nodes
        terminals = graph.get('terminals', [])[:3]
        if terminals:
            flow_html += "<h4>Terminal Nodes:</h4>"
            for term in terminals:
                flow_html += f'<div class="node-box terminal-box">{term}</div>'
        
        flow_html += "</div>"
        
        # Insert custom content into HTML
        insert_point = base_html.find('</head>')
        if insert_point > 0:
            base_html = base_html[:insert_point] + custom_style + base_html[insert_point:]
        
        insert_point = base_html.find('<body>') + 6
        if insert_point > 6:
            base_html = base_html[:insert_point] + summary_html + flow_html + base_html[insert_point:]
        
        return base_html
