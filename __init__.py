#!/usr/bin/env python3
"""
Survey DAG Extractor - Modular LangExtract Implementation
Compliant with survey_dag_schema.json
"""

from pathlib import Path
from typing import Dict, Any, Optional, Literal
import json
from datetime import datetime
import os
from dotenv import load_dotenv

from .config import ExtractorConfig
from .nodes import NodeExtractor
from .edges import EdgeExtractor  
from .predicates import PredicateGenerator
from .validation import DAGValidator
from .assembly import DAGAssembler
from .visualization import DAGVisualizer

# Load environment variables
load_dotenv()


class SurveyDAGExtractor:
    """
    Main orchestrator for survey DAG extraction.
    Uses LangExtract with modular components.
    """
    
    def __init__(
        self,
        primary_model: Literal["gpt-4o", "claude-3-5-sonnet"] = "gpt-4o",
        secondary_model: Literal["gpt-4o-mini", "claude-3-haiku"] = "gpt-4o-mini",
        debug: bool = False
    ):
        """
        Initialize with model configuration.
        
        Args:
            primary_model: For complex extraction tasks
            secondary_model: For simpler tasks (cost optimization)
            debug: Enable debug output
        """
        self.config = ExtractorConfig(
            primary_model=primary_model,
            secondary_model=secondary_model,
            debug=debug
        )
        
        # Initialize components
        self.node_extractor = NodeExtractor(self.config)
        self.edge_extractor = EdgeExtractor(self.config)
        self.predicate_gen = PredicateGenerator(self.config)
        self.validator = DAGValidator(self.config)
        self.assembler = DAGAssembler(self.config)
        self.visualizer = DAGVisualizer(self.config)
        
        print(f"🚀 Survey DAG Extractor initialized")
        print(f"   Primary model: {primary_model}")
        print(f"   Secondary model: {secondary_model}")
    
    def extract(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        validate: bool = True,
        visualize: bool = True
    ) -> Dict[str, Any]:
        """
        Extract complete survey DAG from PDF.
        
        Args:
            pdf_path: Path to survey PDF
            output_dir: Directory for output files
            validate: Run validation checks
            visualize: Generate HTML visualization
            
        Returns:
            Complete survey DAG matching schema
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Setup output directory
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = pdf_path.parent
        
        survey_name = pdf_path.stem
        print(f"\n{'='*60}")
        print(f"📊 Extracting Survey: {survey_name}")
        print(f"{'='*60}")
        
        try:
            # Step 1: Extract nodes
            print(f"\n📝 Phase 1: Extracting Survey Elements")
            nodes = self.node_extractor.extract(pdf_path)
            print(f"   ✓ Extracted {len(nodes)} nodes")
            
            # Step 2: Extract edges  
            print(f"\n🔀 Phase 2: Extracting Routing Logic")
            edges = self.edge_extractor.extract(pdf_path, nodes)
            print(f"   ✓ Extracted {len(edges)} edges")
            
            # Step 3: Generate predicates
            print(f"\n🏷️ Phase 3: Generating Predicates")
            predicates = self.predicate_gen.generate(nodes, edges)
            print(f"   ✓ Generated {len(predicates)} predicates")
            
            # Step 4: Assemble DAG
            print(f"\n🔨 Phase 4: Assembling DAG Structure")
            dag = self.assembler.assemble(
                nodes=nodes,
                edges=edges,
                predicates=predicates,
                metadata=self._create_metadata(pdf_path)
            )
            
            # Step 5: Validate
            if validate:
                print(f"\n✅ Phase 5: Validating DAG")
                validation_result = self.validator.validate(dag)
                if validation_result['is_valid']:
                    print(f"   ✓ Validation passed")
                else:
                    print(f"   ⚠️ Validation issues found:")
                    for issue in validation_result['issues'][:5]:
                        print(f"      - {issue}")
                
                # Add validation to metadata
                dag['survey_dag']['metadata']['build']['validation_passed'] = validation_result['is_valid']
                dag['survey_dag']['validation'] = validation_result
            
            # Step 6: Save outputs
            print(f"\n💾 Phase 6: Saving Outputs")
            
            # Save DAG JSON
            dag_path = output_dir / f"{survey_name}_dag.json"
            with open(dag_path, 'w') as f:
                json.dump(dag, f, indent=2)
            print(f"   ✓ DAG saved to: {dag_path}")
            
            # Save JSONL for LangExtract
            jsonl_path = output_dir / f"{survey_name}_extracted.jsonl"
            self._save_jsonl(dag, jsonl_path)
            print(f"   ✓ JSONL saved to: {jsonl_path}")
            
            # Generate visualization
            if visualize:
                print(f"\n🎨 Phase 7: Generating Visualization")
                html_path = self.visualizer.generate(dag, output_dir / f"{survey_name}_viz.html")
                print(f"   ✓ Visualization saved to: {html_path}")
            
            # Summary
            print(f"\n{'='*60}")
            print(f"✨ Extraction Complete!")
            print(f"{'='*60}")
            self._print_summary(dag)
            
            return dag
            
        except Exception as e:
            print(f"\n❌ Extraction failed: {e}")
            if self.config.debug:
                import traceback
                traceback.print_exc()
            raise
    
    def _create_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Create metadata section per schema."""
        return {
            "id": pdf_path.stem.lower().replace(' ', '_'),
            "title": pdf_path.stem.replace('_', ' '),
            "version": datetime.now().strftime("%Y-%m"),
            "objective": "edge",  # Default to edge coverage
            "build": {
                "extractor_version": "2.0.0-langextract",
                "extracted_at": datetime.now().isoformat() + "Z",
                "method": "llm_extraction",
                "primary_model": self.config.primary_model,
                "secondary_model": self.config.secondary_model,
                "source_format": "pdf",
                "validation_passed": False,  # Will be updated
                "post_edit": False
            }
        }
    
    def _save_jsonl(self, dag: Dict, path: Path):
        """Save in LangExtract JSONL format."""
        with open(path, 'w') as f:
            # Each line is a document with extractions
            doc = {
                "text": f"Survey: {dag['survey_dag']['metadata']['title']}",
                "extractions": [],
                "metadata": dag['survey_dag']['metadata']
            }
            
            # Add nodes as extractions
            for node in dag['survey_dag']['graph']['nodes']:
                doc['extractions'].append({
                    "extraction_class": "node",
                    "extraction_text": node['id'],
                    "attributes": node
                })
            
            # Add edges as extractions
            for edge in dag['survey_dag']['graph']['edges']:
                doc['extractions'].append({
                    "extraction_class": "edge",
                    "extraction_text": f"{edge['source']} → {edge['target']}",
                    "attributes": edge
                })
            
            json.dump(doc, f)
    
    def _print_summary(self, dag: Dict):
        """Print extraction summary."""
        graph = dag['survey_dag']['graph']
        preds = dag['survey_dag']['predicates']
        
        # Count node types
        node_types = {}
        for node in graph['nodes']:
            t = node.get('type', 'unknown')
            node_types[t] = node_types.get(t, 0) + 1
        
        # Count edge types
        edge_types = {}
        for edge in graph['edges']:
            t = edge.get('subkind', 'unknown')
            edge_types[t] = edge_types.get(t, 0) + 1
        
        print(f"\n📊 Summary Statistics:")
        print(f"   Nodes: {len(graph['nodes'])}")
        for t, count in node_types.items():
            print(f"      - {t}: {count}")
        
        print(f"   Edges: {len(graph['edges'])}")
        for t, count in edge_types.items():
            print(f"      - {t}: {count}")
        
        print(f"   Predicates: {len(preds)}")
        print(f"   Start node: {graph.get('start', 'Not identified')}")
        print(f"   Terminals: {len(graph.get('terminals', []))}")


def extract_survey(
    pdf_path: str,
    output_dir: Optional[str] = None,
    primary_model: str = "gpt-4o",
    validate: bool = True,
    visualize: bool = True,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Convenience function for extraction.
    
    Example:
        dag = extract_survey("survey.pdf", output_dir="output/")
    """
    extractor = SurveyDAGExtractor(
        primary_model=primary_model,
        debug=debug
    )
    
    return extractor.extract(
        pdf_path=pdf_path,
        output_dir=output_dir,
        validate=validate,
        visualize=visualize
    )


__all__ = ['SurveyDAGExtractor', 'extract_survey']
