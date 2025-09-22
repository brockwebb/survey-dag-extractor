#!/usr/bin/env python3
"""
DAG Configuration Manager - Load survey-specific configurations
"""

import json
from pathlib import Path
from typing import Dict, Any, List

class DAGConfig:
    """Manages survey-specific DAG configuration."""
    
    def __init__(self, config_path: str = None):
        """Initialize with config file path."""
        if config_path is None:
            # Default to HTOPS config
            config_path = Path(__file__).parent / "htops_dag_config.json"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"DAG config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    # Survey Metadata
    def get_survey_id(self) -> str:
        return self.config['survey_metadata']['id']
    
    def get_survey_title(self) -> str:
        return self.config['survey_metadata']['title']
    
    def get_survey_version(self) -> str:
        return self.config['survey_metadata']['version']
    
    def get_objective(self) -> str:
        return self.config['survey_metadata']['objective']
    
    # DAG Structure
    def get_start_node(self) -> str:
        return self.config['dag_structure']['start_node']
    
    def get_completion_terminals(self) -> List[str]:
        return self.config['dag_structure']['completion_terminals']
    
    def get_early_exit_terminals(self) -> List[str]:
        return self.config['dag_structure']['early_exit_terminals']
    
    def get_intermediate_terminals(self) -> List[str]:
        return self.config['dag_structure']['intermediate_terminals']
    
    def get_all_terminals(self) -> List[str]:
        """Get all terminal types combined."""
        return (self.get_completion_terminals() + 
                self.get_early_exit_terminals() + 
                self.get_intermediate_terminals())
    
    # Path Classification
    def classify_terminal(self, terminal: str) -> Dict[str, Any]:
        """Classify a terminal according to survey methodology."""
        
        # Check optimal paths
        if terminal in self.config['path_classification']['optimal_paths']['terminals']:
            return self.config['path_classification']['optimal_paths']
        
        # Check avoid paths
        if terminal in self.config['path_classification']['avoid_paths']['terminals']:
            return self.config['path_classification']['avoid_paths']
        
        # Check neutral paths
        if terminal in self.config['path_classification']['neutral_paths']['terminals']:
            return self.config['path_classification']['neutral_paths']
        
        # Default to neutral
        return self.config['path_classification']['neutral_paths']
    
    # Validation Rules
    def allow_terminal_chains(self) -> bool:
        return self.config['validation_rules']['allow_terminal_chains']
    
    def require_single_start(self) -> bool:
        return self.config['validation_rules']['require_single_start']
    
    def require_single_ultimate_terminal(self) -> bool:
        return self.config['validation_rules']['require_single_ultimate_terminal']
    
    def get_terminal_naming_patterns(self) -> List[str]:
        return self.config['validation_rules']['terminal_naming_patterns']
    
    # Coverage Settings
    def get_max_paths(self) -> int:
        return self.config['coverage_settings']['max_paths']
    
    def get_max_depth(self) -> int:
        return self.config['coverage_settings']['max_depth']
    
    def get_coverage_objective(self) -> str:
        return self.config['coverage_settings']['objective']
    
    def get_coverage_algorithm(self) -> str:
        return self.config['coverage_settings']['algorithm']


def create_config_for_survey(survey_id: str, survey_title: str, 
                           start_node: str = "START",
                           completion_terminals: List[str] = None,
                           early_exit_terminals: List[str] = None) -> DAGConfig:
    """Create a new DAG config for a survey."""
    
    if completion_terminals is None:
        completion_terminals = ["SURVEY_COMPLETE"]
    if early_exit_terminals is None:
        early_exit_terminals = ["END", "TERMINATE"]
    
    config_data = {
        "survey_metadata": {
            "id": survey_id,
            "title": survey_title,
            "version": "1.1",
            "objective": "edge"
        },
        "dag_structure": {
            "start_node": start_node,
            "completion_terminals": completion_terminals,
            "early_exit_terminals": early_exit_terminals,
            "intermediate_terminals": [],
            "system_terminals": []
        },
        "path_classification": {
            "optimal_paths": {
                "terminals": completion_terminals,
                "priority": 1,
                "survey_value": "HIGH",
                "methodology_note": "Desired outcome - full survey completion"
            },
            "avoid_paths": {
                "terminals": early_exit_terminals,
                "priority": 3,
                "survey_value": "LOW", 
                "methodology_note": "Early termination - minimize in deployment"
            },
            "neutral_paths": {
                "terminals": [],
                "priority": 2,
                "survey_value": "MEDIUM",
                "methodology_note": "Other termination path"
            }
        },
        "validation_rules": {
            "allow_terminal_chains": True,
            "require_single_start": True,
            "require_single_ultimate_terminal": True,
            "terminal_naming_patterns": [
                "^SURVEY_COMPLETE$",
                "^[A-Z][A-Z0-9_]*$"
            ]
        },
        "coverage_settings": {
            "max_paths": 100,
            "max_depth": 50,
            "objective": "edge",
            "algorithm": "survey_aware_depth_first_search"
        }
    }
    
    # Save config file
    config_path = Path(__file__).parent / f"{survey_id}_dag_config.json"
    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    return DAGConfig(str(config_path))


if __name__ == "__main__":
    # Example usage
    config = DAGConfig()
    print(f"Survey: {config.get_survey_title()}")
    print(f"Start: {config.get_start_node()}")
    print(f"Completion terminals: {config.get_completion_terminals()}")
    print(f"Early exit terminals: {config.get_early_exit_terminals()}")
    
    # Test classification
    print(f"\\nSURVEY_COMPLETE classification: {config.classify_terminal('SURVEY_COMPLETE')}")
    print(f"END classification: {config.classify_terminal('END')}")
