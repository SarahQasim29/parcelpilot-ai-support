# test_data.py
import pandas as pd
import os

# Check if file exists
excel_path = "data/structured/ParcelPilot_Assessment_Data.xlsx"
print(f"📁 Checking: {excel_path}")
print(f"Exists: {os.path.exists(excel_path)}")

if os.path.exists(excel_path):
    # Load all sheets
    xls = pd.ExcelFile(excel_path)
    print(f"\n📊 Sheets found: {xls.sheet_names}")
    
    for sheet in xls.sheet_names:
        df = pd.read_excel(excel_path, sheet_name=sheet)
        print(f"\n📋 Sheet: {sheet}")
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {list(df.columns)}")
        print(f"   First row: {df.iloc[0].to_dict() if not df.empty else 'Empty'}")