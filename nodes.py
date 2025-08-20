"""
Node Extraction Module using LangExtract
Extracts survey elements (questions, instructions, terminals)
"""

import langextract as lx
import textwrap
from pathlib import Path
from typing import List, Dict, Any
import PyPDF2

from .config import ExtractorConfig


class NodeExtractor:
    """
    Extracts nodes from survey PDF using LangExtract.
    """
    
    def __init__(self, config: ExtractorConfig):
        self.config = config
        
    def extract(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        Extract all nodes from survey PDF.
        
        Returns:
            List of nodes matching schema format
        """
        # Extract text from PDF
        survey_text = self._extract_pdf_text(pdf_path)
        
        # Use primary model for complex extraction
        model_id = self.config.get_model_id(use_secondary=False)
        
        # Define extraction prompt
        prompt = textwrap.dedent("""
        Extract ALL survey elements from this document.
        
        For each element (question, instruction, terminal), extract:
        1. The EXACT ID as it appears (Q1, FD1, EMP2, END_SURVEY, etc.)
        2. The complete text/content
        3. The type (question, instruction, terminal)
        4. Response options with their numeric codes
        5. Display conditions (when should this appear)
        6. Section/block it belongs to
        7. Order in the survey flow
        
        CRITICAL:
        - Terminal nodes must have IDs starting with END_
        - Capture universe conditions EXACTLY as written
        - Include ALL response option codes
        - Don't paraphrase - use exact text
        """)
        
        # Define examples for LangExtract
        examples = self._create_node_examples()
        
        # Extract using LangExtract
        result = lx.extract(
            text_or_documents=survey_text,
            prompt_description=prompt,
            examples=examples,
            model_id=model_id,
            max_char_buffer=self.config.max_char_buffer,
            max_workers=self.config.max_workers
        )
        
        # Convert extractions to schema-compliant nodes
        nodes = []
        seen_ids = set()
        order_index = 0
        
        for doc in result.documents:
            for extraction in doc.extractions:
                if extraction.extraction_class == "survey_element":
                    node_id = extraction.extraction_text.strip()
                    
                    # Deduplicate
                    if node_id in seen_ids:
                        continue
                    seen_ids.add(node_id)
                    
                    order_index += 1
                    node = self._create_node(extraction, order_index)
                    nodes.append(node)
        
        # Post-process to identify special nodes
        nodes = self._identify_special_nodes(nodes)
        
        if self.config.debug:
            print(f"   Debug: Extracted {len(nodes)} unique nodes")
            print(f"   Debug: Node IDs: {list(seen_ids)[:10]}...")
        
        return nodes
    
    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text from PDF file."""
        text = ""
        
        with open(pdf_path, 'rb') as file:
            pdf = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf.pages)):
                page = pdf.pages[page_num]
                text += f"\n\n--- Page {page_num + 1} ---\n\n"
                text += page.extract_text()
        
        return text
    
    def _create_node_examples(self) -> List[lx.data.ExampleData]:
        """Create examples for node extraction."""
        return [
            lx.data.ExampleData(
                text="""Q1. Is [NAME] correct?
                (1) Yes
                (2) No, this is a different person 
                (3) Don't know this person""",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="survey_element",
                        extraction_text="Q1",
                        attributes={
                            "full_text": "Is [NAME] correct?",
                            "type": "question",
                            "response_type": "single_choice",
                            "response_options": [
                                {"code": 1, "text": "Yes"},
                                {"code": 2, "text": "No, this is a different person"},
                                {"code": 3, "text": "Don't know this person"}
                            ],
                            "display_condition": "always_show",
                            "section": "verification"
                        }
                    )
                ]
            ),
            lx.data.ExampleData(
                text="""Universe: D11 > 0
                FD1. In the last 7 days, which statement best describes the food eaten in your household?
                (1) Enough of the kinds of food we wanted
                (2) Enough, but not always the kinds we wanted
                (3) Sometimes not enough to eat
                (4) Often not enough to eat""",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="survey_element",
                        extraction_text="FD1",
                        attributes={
                            "full_text": "In the last 7 days, which statement best describes the food eaten in your household?",
                            "type": "question",
                            "response_type": "single_choice",
                            "response_options": [
                                {"code": 1, "text": "Enough of the kinds of food we wanted"},
                                {"code": 2, "text": "Enough, but not always the kinds we wanted"},
                                {"code": 3, "text": "Sometimes not enough to eat"},
                                {"code": 4, "text": "Often not enough to eat"}
                            ],
                            "display_condition": "D11 > 0",
                            "universe": "D11 > 0",
                            "section": "food_security"
                        }
                    )
                ]
            ),
            lx.data.ExampleData(
                text="END_SURVEY: Thank you for completing this survey. Your responses have been recorded.",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="survey_element",
                        extraction_text="END_SURVEY",
                        attributes={
                            "full_text": "Thank you for completing this survey. Your responses have been recorded.",
                            "type": "terminal",
                            "section": "closing"
                        }
                    )
                ]
            )
        ]
    
    def _create_node(self, extraction: lx.data.Extraction, order: int) -> Dict[str, Any]:
        """Convert extraction to schema-compliant node."""
        attrs = extraction.attributes
        node_id = extraction.extraction_text.strip()
        
        # Determine node type
        node_type = attrs.get('type', 'question')
        if node_id.startswith('END_') or node_type == 'terminal':
            node_type = 'terminal'
        elif node_type == 'instruction':
            node_type = 'junction'
        else:
            node_type = 'question'
        
        # Create domain
        domain = self._create_domain(attrs)
        
        # Create universe
        universe = {
            "expression": attrs.get('display_condition', 'always_show')
        }
        if attrs.get('universe'):
            universe['natural_language'] = attrs['universe']
        
        return {
            "id": node_id,
            "type": node_type,
            "order_index": order,
            "block": attrs.get('section', 'main'),
            "domain": domain,
            "metadata": {
                "text": attrs.get('full_text', ''),
                "variable_name": node_id,
                "response_type": attrs.get('response_type', '')
            },
            "universe": universe,
            "provenance": {
                "source_id": str(Path(extraction.document_id).name) if hasattr(extraction, 'document_id') else "survey.pdf",
                "locators": [
                    {"type": "char_offset", "value": f"{extraction.char_start}-{extraction.char_end}"}
                ] if hasattr(extraction, 'char_start') else [],
                "confidence": 0.95,
                "method": "llm_extraction",
                "human_verified": False
            }
        }
    
    def _create_domain(self, attrs: Dict) -> Dict[str, Any]:
        """Create domain from response options."""
        response_type = attrs.get('response_type', '')
        options = attrs.get('response_options', [])
        
        # Determine domain kind
        if 'single' in response_type:
            kind = 'enum'
        elif 'multi' in response_type:
            kind = 'set'
        elif 'text' in response_type:
            kind = 'text'
        elif 'numeric' in response_type:
            kind = 'numeric'
        elif 'date' in response_type:
            kind = 'date'
        elif attrs.get('type') == 'terminal':
            kind = 'terminal'
        else:
            kind = 'text'
        
        domain = {"kind": kind}
        
        # Extract values for enum/set
        if kind in ['enum', 'set'] and options:
            values = []
            for opt in options:
                if isinstance(opt, dict) and 'code' in opt:
                    values.append(opt['code'])
                elif isinstance(opt, int):
                    values.append(opt)
            
            if values:
                domain['values'] = values
        
        return domain
    
    def _identify_special_nodes(self, nodes: List[Dict]) -> List[Dict]:
        """Identify start and terminal nodes."""
        
        # Find start node
        start_identified = False
        for node in nodes:
            text = node['metadata'].get('text', '').lower()
            if any(phrase in text for phrase in ['welcome', 'thank you for participating', 'introduction']):
                node['_is_start'] = True
                start_identified = True
                break
        
        # If no start found, use first non-terminal
        if not start_identified:
            for node in nodes:
                if node['type'] != 'terminal':
                    node['_is_start'] = True
                    break
        
        return nodes
