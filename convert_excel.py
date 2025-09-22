#!/usr/bin/env python3
"""
Quick Excel to JSON converter for HTOPS data dictionary.
Run this to convert the Excel file before using the agents.
"""

import pandas as pd
import json
from pathlib import Path
import sys

def convert_excel_to_json():
    """Convert HTOPS Excel data dictionary to JSON."""
    
    # Paths
    excel_path = Path(__file__).parent / "data" / "HTOPS_data_dictionary.xlsx"
    json_path = Path(__file__).parent / "data" / "htops_data_dictionary.json"
    
    print(f"🔄 Converting {excel_path.name} to JSON...")
    
    if not excel_path.exists():
        print(f"❌ Excel file not found: {excel_path}")
        return False
    
    try:
        # Read Excel - try common sheet names
        sheet_names = ["PUF Data Dictionary", "Data Dictionary", "Sheet1"]
        df = None
        
        for sheet in sheet_names:
            try:
                df = pd.read_excel(excel_path, sheet_name=sheet)
                print(f"   ✅ Using sheet: {sheet}")
                break
            except:
                continue
        
        if df is None:
            # Try reading the first sheet
            df = pd.read_excel(excel_path, sheet_name=0)
            print(f"   ✅ Using first sheet")
        
        print(f"   📊 Loaded {len(df)} rows, {len(df.columns)} columns")
        print(f"   📋 Columns: {list(df.columns)[:5]}..." if len(df.columns) > 5 else f"   📋 Columns: {list(df.columns)}")
        
        # Convert to structured JSON
        variables = []
        
        for idx, row in df.iterrows():
            # Extract first few columns as key fields
            cols = list(df.columns)
            
            variable_record = {
                "variable_name": str(row[cols[0]]) if pd.notna(row[cols[0]]) else f"VAR_{idx}",
                "description": str(row[cols[1]]) if len(cols) > 1 and pd.notna(row[cols[1]]) else None,
                "data_type": str(row[cols[2]]) if len(cols) > 2 and pd.notna(row[cols[2]]) else None,
                "values": str(row[cols[3]]) if len(cols) > 3 and pd.notna(row[cols[3]]) else None,
                "row_index": idx
            }
            
            # Skip empty rows
            if variable_record["variable_name"] in ["nan", "None", ""]:
                continue
            
            variables.append(variable_record)
        
        # Create final JSON structure
        result = {
            "metadata": {
                "source_file": excel_path.name,
                "total_variables": len(variables),
                "columns": list(df.columns),
                "converted_at": pd.Timestamp.now().isoformat()
            },
            "variables": variables
        }
        
        # Save JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ Saved JSON: {json_path.name}")
        print(f"   📊 Variables converted: {len(variables)}")
        
        # Show sample
        if variables:
            print(f"\n📋 Sample Variables:")
            for var in variables[:3]:
                print(f"   • {var['variable_name']}: {var.get('description', 'No description')}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Conversion failed: {e}")
        return False

if __name__ == "__main__":
    success = convert_excel_to_json()
    sys.exit(0 if success else 1)
