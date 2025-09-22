#!/usr/bin/env python3
"""
Data Dictionary Converter - Excel to JSON

Converts HTOPS data dictionary from Excel format to JSON for agent processing.

Usage:
    python convert_data_dictionary.py --input data/HTOPS_data_dictionary.xlsx --output data/htops_data_dictionary.json
"""

import pandas as pd
import json
import argparse
from pathlib import Path

def convert_excel_to_json(excel_file: Path, output_file: Path) -> dict:
    """Convert Excel data dictionary to structured JSON."""
    
    print(f"📚 Converting data dictionary: {excel_file}")
    
    try:
        # Read Excel file - try different sheet names
        possible_sheets = ["PUF Data Dictionary", "Data Dictionary", "Sheet1", 0]
        
        df = None
        sheet_used = None
        
        for sheet in possible_sheets:
            try:
                df = pd.read_excel(excel_file, sheet_name=sheet)
                sheet_used = sheet
                print(f"   ✅ Found data in sheet: {sheet}")
                break
            except:
                continue
        
        if df is None:
            raise ValueError("Could not find data dictionary sheet")
        
        print(f"   📊 Loaded {len(df)} variables")
        print(f"   📋 Columns: {list(df.columns)}")
        
        # Convert to structured format
        variables = []
        
        for idx, row in df.iterrows():
            # Handle different possible column names
            variable_name = None
            description = None
            data_type = None
            values = None
            
            # Try different column name patterns
            for col in df.columns:
                col_lower = str(col).lower()
                if 'variable' in col_lower or 'name' in col_lower:
                    variable_name = str(row[col]) if pd.notna(row[col]) else None
                elif 'description' in col_lower or 'label' in col_lower or 'text' in col_lower:
                    description = str(row[col]) if pd.notna(row[col]) else None
                elif 'type' in col_lower or 'format' in col_lower:
                    data_type = str(row[col]) if pd.notna(row[col]) else None
                elif 'value' in col_lower or 'code' in col_lower or 'response' in col_lower:
                    values = str(row[col]) if pd.notna(row[col]) else None
            
            # Skip empty rows
            if not variable_name or variable_name.lower() in ['nan', 'none', '']:
                continue
            
            variable_record = {
                "variable_name": variable_name,
                "description": description,
                "data_type": data_type,
                "values": values,
                "row_index": idx
            }
            
            # Add all columns for reference
            variable_record["raw_data"] = {}
            for col in df.columns:
                if pd.notna(row[col]):
                    variable_record["raw_data"][str(col)] = str(row[col])
            
            variables.append(variable_record)
        
        # Create final JSON structure
        result = {
            "metadata": {
                "source_file": str(excel_file),
                "sheet_used": str(sheet_used),
                "total_variables": len(variables),
                "columns": list(df.columns),
                "converted_at": pd.Timestamp.now().isoformat()
            },
            "variables": variables
        }
        
        # Save JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ Saved JSON: {output_file}")
        print(f"   📊 Variables converted: {len(variables)}")
        
        # Show sample variables
        print(f"\n📋 Sample Variables:")
        for var in variables[:3]:
            print(f"   • {var['variable_name']}: {var.get('description', 'No description')[:60]}...")
        
        return result
        
    except Exception as e:
        print(f"   ❌ Conversion failed: {e}")
        raise

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Convert Excel data dictionary to JSON")
    parser.add_argument("--input", required=True, help="Input Excel file")
    parser.add_argument("--output", required=True, help="Output JSON file")
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    output_file = Path(args.output)
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return 1
    
    try:
        result = convert_excel_to_json(input_file, output_file)
        print(f"\n✅ Data dictionary conversion complete!")
        print(f"📁 Output: {output_file}")
        return 0
    except Exception as e:
        print(f"\n❌ Conversion failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
