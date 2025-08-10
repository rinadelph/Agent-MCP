#!/usr/bin/env python3
"""
Beverly Knits ERP System Runner
Loads real production data and starts the system
"""

import os
import sys
import json
from pathlib import Path
import subprocess

# Set environment variables
PROJECT_DIR = Path("/mnt/c/Users/psytz/TMUX Final/Agent-MCP")
DATA_DIR = PROJECT_DIR / "ERP Data" / "New folder"

os.environ["MCP_PROJECT_DIR"] = str(PROJECT_DIR)
os.environ["BEVERLY_DATA_PATH"] = str(DATA_DIR)

print("🏭 BEVERLY KNITS ERP SYSTEM")
print("=" * 60)
print(f"Project: {PROJECT_DIR}")
print(f"Data: {DATA_DIR}")
print()

# Check data files
print("📊 Checking production data files...")
critical_files = [
    "yarn_inventory (1).xlsx",
    "Yarn_Demand_By_Style.xlsx", 
    "BOM_2(Sheet1).csv",
    "eFab_Inventory_G00_20250804.xlsx",
    "eFab_Inventory_G02_20250804.xlsx",
    "eFab_Inventory_I01_20250804.xlsx",
    "eFab_Inventory_F01_20250804 (1).xlsx",
    "eFab_Inventory_P01_20250808.xlsx",
    "Sales Activity Report (4).xlsx",
    "QuadS_finishedFabricList_ (2) (1).xlsx"
]

missing_files = []
for file in critical_files:
    file_path = DATA_DIR / file
    if file_path.exists():
        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"  ✅ {file} ({size_mb:.1f} MB)")
    else:
        print(f"  ❌ {file} (MISSING)")
        missing_files.append(file)

if missing_files:
    print(f"\n⚠️ Warning: {len(missing_files)} files missing")
else:
    print(f"\n✅ All {len(critical_files)} critical data files found")

print()
print("🚀 Starting Beverly Knits ERP System...")
print("=" * 60)

# Create a simple Flask app to serve the data
app_code = '''
from flask import Flask, jsonify, render_template_string
import pandas as pd
from pathlib import Path
import os

app = Flask(__name__)
DATA_PATH = Path(os.environ.get("BEVERLY_DATA_PATH", "."))

@app.route("/")
def index():
    return """
    <html>
    <head>
        <title>Beverly Knits ERP</title>
        <style>
            body { font-family: Arial; margin: 20px; background: #f5f5f5; }
            h1 { color: #2c3e50; }
            .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metric { display: inline-block; margin: 10px 20px; }
            .value { font-size: 24px; font-weight: bold; color: #27ae60; }
            .label { color: #7f8c8d; font-size: 12px; }
            table { width: 100%; border-collapse: collapse; }
            th { background: #34495e; color: white; padding: 10px; text-align: left; }
            td { padding: 8px; border-bottom: 1px solid #ecf0f1; }
            .stage { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
            .g00 { background: #3498db; color: white; }
            .g02 { background: #9b59b6; color: white; }
            .i01 { background: #e67e22; color: white; }
            .f01 { background: #27ae60; color: white; }
            .p01 { background: #c0392b; color: white; }
        </style>
    </head>
    <body>
        <h1>🏭 Beverly Knits ERP System</h1>
        <div class="card">
            <h2>Production Pipeline Status</h2>
            <div class="metric"><div class="value" id="g00">-</div><div class="label">G00 Grey Fabric</div></div>
            <div class="metric"><div class="value" id="g02">-</div><div class="label">G02 Dyed Fabric</div></div>
            <div class="metric"><div class="value" id="i01">-</div><div class="label">I01 Inspected</div></div>
            <div class="metric"><div class="value" id="f01">-</div><div class="label">F01 Finished</div></div>
            <div class="metric"><div class="value" id="p01">-</div><div class="label">P01 Packed</div></div>
        </div>
        <div class="card">
            <h2>Yarn Inventory</h2>
            <table id="yarn-table">
                <tr><th>Loading...</th></tr>
            </table>
        </div>
        <div class="card">
            <h2>Sales Orders</h2>
            <table id="sales-table">
                <tr><th>Loading...</th></tr>
            </table>
        </div>
        <script>
            fetch('/api/status').then(r => r.json()).then(data => {
                document.getElementById('g00').textContent = data.inventory.g00.toLocaleString();
                document.getElementById('g02').textContent = data.inventory.g02.toLocaleString();
                document.getElementById('i01').textContent = data.inventory.i01.toLocaleString();
                document.getElementById('f01').textContent = data.inventory.f01.toLocaleString();
                document.getElementById('p01').textContent = data.inventory.p01.toLocaleString();
            });
            
            fetch('/api/yarn').then(r => r.json()).then(data => {
                let table = '<tr><th>Yarn ID</th><th>Description</th><th>Inventory</th><th>Supplier</th></tr>';
                data.yarns.forEach(y => {
                    table += `<tr><td>${y.id}</td><td>${y.desc}</td><td>${y.qty}</td><td>${y.supplier}</td></tr>`;
                });
                document.getElementById('yarn-table').innerHTML = table;
            });
            
            fetch('/api/sales').then(r => r.json()).then(data => {
                let table = '<tr><th>Order #</th><th>Customer</th><th>Style</th><th>Quantity</th><th>Status</th></tr>';
                data.orders.forEach(o => {
                    table += `<tr><td>${o.order}</td><td>${o.customer}</td><td>${o.style}</td><td>${o.qty}</td><td><span class="stage ${o.stage}">${o.stage}</span></td></tr>`;
                });
                document.getElementById('sales-table').innerHTML = table;
            });
        </script>
    </body>
    </html>
    """

@app.route("/api/status")
def status():
    inventory = {}
    stages = ["g00", "g02", "i01", "f01", "p01"]
    for stage in stages:
        files = list(DATA_PATH.glob(f"*_{stage.upper()}_*.xlsx"))
        if files:
            try:
                df = pd.read_excel(files[0])
                inventory[stage] = len(df)
            except:
                inventory[stage] = 0
        else:
            inventory[stage] = 0
    
    return jsonify({
        "status": "running",
        "data_path": str(DATA_PATH),
        "inventory": inventory
    })

@app.route("/api/yarn")
def yarn():
    yarn_file = DATA_PATH / "yarn_inventory (1).xlsx"
    yarns = []
    if yarn_file.exists():
        try:
            df = pd.read_excel(yarn_file)
            for _, row in df.head(10).iterrows():
                yarns.append({
                    "id": str(row.get("Desc#", "")),
                    "desc": str(row.get("Description", "")),
                    "qty": str(row.get("Inventory", 0)),
                    "supplier": str(row.get("Supplier", ""))
                })
        except Exception as e:
            print(f"Error loading yarn: {e}")
    return jsonify({"yarns": yarns})

@app.route("/api/sales")
def sales():
    sales_file = DATA_PATH / "Sales Activity Report (4).xlsx"
    orders = []
    if sales_file.exists():
        try:
            df = pd.read_excel(sales_file)
            for _, row in df.head(10).iterrows():
                orders.append({
                    "order": str(row.get("Document", "")),
                    "customer": str(row.get("Customer", "")),
                    "style": str(row.get("Style", "")),
                    "qty": str(row.get("Qty Shipped", 0)),
                    "stage": "f01"
                })
        except Exception as e:
            print(f"Error loading sales: {e}")
    return jsonify({"orders": orders})

if __name__ == "__main__":
    print(f"Starting Beverly Knits ERP on http://localhost:5000")
    print(f"Data path: {DATA_PATH}")
    app.run(host="0.0.0.0", port=5000, debug=False)
'''

# Write the Flask app
app_file = PROJECT_DIR / "beverly_app.py"
with open(app_file, "w") as f:
    f.write(app_code)

print(f"Created app file: {app_file}")
print()
print("Starting server on http://localhost:5000")
print("Press Ctrl+C to stop")
print("-" * 60)

# Run the Flask app
try:
    subprocess.run([sys.executable, str(app_file)], env=os.environ)
except KeyboardInterrupt:
    print("\n\nServer stopped.")