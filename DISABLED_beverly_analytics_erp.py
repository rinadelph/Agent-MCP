#!/usr/bin/env python3
"""
Beverly Knits AI-Enhanced ERP System
Production-ready supply chain optimization with business analytics
"""

from flask import Flask, jsonify, render_template_string, request
import pandas as pd
import numpy as np
from pathlib import Path
import os
from datetime import datetime, timedelta
import json
from collections import defaultdict

app = Flask(__name__)
DATA_PATH = Path("ERP Data/New folder")

class SupplyChainAnalyzer:
    """Business intelligence and analytics engine"""
    COST_PER_POUND_COL = 'Cost/Pound'
    
    def __init__(self, data_path):
        self.data_path = data_path
        self.yarn_data = None
        self.sales_data = None
        self.inventory_data = {}
        self.load_data()
    
    def load_data(self):
        """Load and process all ERP data"""
        try:
            # Load yarn inventory
            yarn_file = self.data_path / "yaiern_inventory (1).xlsx"
            if yarn_file.exists():
                self.yarn_data = pd.read_excel(yarn_file)
                
            # Load sales data
            sales_file = self.data_path / "Sales Activity Report (4).xlsx"
            if sales_file.exists():
                self.sales_data = pd.read_excel(sales_file)
                
            # Load inventory stages
            for stage in ["G00", "G02", "I01", "F01", "P01"]:
                stage_files = list(self.data_path.glob(f"*_{stage}_*.xlsx"))
                if stage_files:
                    self.inventory_data[stage] = pd.read_excel(stage_files[0])
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def calculate_kpis(self):
        """Calculate key performance indicators"""
        kpis = {}
        
        if self.yarn_data is not None:
            # Inventory metrics
            total_inventory_value = (self.yarn_data['Planning Balance'] * 
                                   self.yarn_data[self.COST_PER_POUND_COL]).sum()
            kpis['inventory_value'] = f"${total_inventory_value:,.0f}"
            
            # Inventory turns (assuming 12 months)
            consumed = self.yarn_data['Consumed'].sum()
            avg_inventory = self.yarn_data['Planning Balance'].sum()
            inventory_turns = consumed / max(avg_inventory, 1) if avg_inventory > 0 else 0
            kpis['inventory_turns'] = f"{inventory_turns:.1f}x"
            
            # Low stock alerts
            low_stock_items = len(self.yarn_data[self.yarn_data['Planning Balance'] < 1000])
            kpis['low_stock_alerts'] = low_stock_items
            
            # Supplier diversity
            unique_suppliers = self.yarn_data['Supplier'].nunique()
            kpis['supplier_count'] = unique_suppliers
            
        if self.sales_data is not None:
            # Sales metrics
            total_sales = (self.sales_data['Qty Shipped'] * 
                          self.sales_data['Unit Price']).sum()
            kpis['total_sales'] = f"${total_sales:,.0f}"
            
            # Customer count
            unique_customers = self.sales_data['Customer'].nunique()
            kpis['customer_count'] = unique_customers
            
            # Average order value
            avg_order_value = total_sales / len(self.sales_data) if len(self.sales_data) > 0 else 0
            kpis['avg_order_value'] = f"${avg_order_value:,.0f}"
            
        return kpis
    
    def get_inventory_optimization(self):
        """EOQ and inventory optimization recommendations"""
        recommendations = []
        
        if self.yarn_data is not None:
            # Calculate EOQ for top items
            top_items = self.yarn_data.nlargest(20, 'Consumed')
            
            for _, item in top_items.iterrows():
                annual_demand = item['Consumed'] * 12  # Annualize monthly data
                holding_cost = item[self.COST_PER_POUND_COL] * 0.25  # 25% holding cost
                ordering_cost = 50  # Assumed ordering cost
                
                if annual_demand > 0 and holding_cost > 0:
                    eoq = np.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
                    current_order_qty = item['On Order'] if pd.notna(item['On Order']) else 0
                    
                    recommendation = {
                        'item': str(item['Description'])[:50],
                        'current_stock': int(item['Planning Balance']),
                        'eoq': int(eoq),
                        'annual_demand': int(annual_demand),
                        'savings_potential': abs(current_order_qty - eoq) * item[self.COST_PER_POUND_COL] * 0.1,
                        'action': 'Order More' if current_order_qty < eoq else 'Reduce Order'
                    }
                    recommendations.append(recommendation)
                    
        return sorted(recommendations, key=lambda x: x['savings_potential'], reverse=True)[:10]
    
    def get_supplier_analysis(self):
        """Supplier performance and risk analysis"""
        supplier_metrics = []
        
        if self.yarn_data is not None:
            supplier_stats = self.yarn_data.groupby('Supplier').agg({
                'Planning Balance': 'sum',
                self.COST_PER_POUND_COL: 'mean',
                'Total Cost': 'sum',
                'Desc#': 'count'
            }).round(2)
            
            for supplier, stats in supplier_stats.iterrows():
                risk_score = min(100, max(0, 100 - (stats['Desc#'] * 5)))  # Diversity reduces risk
                
                supplier_metrics.append({
                    'supplier': str(supplier)[:30],
                    'total_value': f"${stats['Total Cost']:,.0f}",
                    'avg_cost': f"${stats[self.COST_PER_POUND_COL]:.2f}",
                    'item_count': int(stats['Desc#']),
                    'risk_score': risk_score,
                    'risk_level': 'High' if risk_score > 70 else 'Medium' if risk_score > 40 else 'Low'
                })
                
        return sorted(supplier_metrics, key=lambda x: x['risk_score'], reverse=True)[:10]
    
    def get_production_insights(self):
        """Production pipeline analysis"""
        insights = []
        
        # Analyze production stages
        stage_names = {
            'G00': 'Grey Fabric',
            'G02': 'Dyed Fabric', 
            'I01': 'Inspected',
            'F01': 'Finished',
            'P01': 'Packed'
        }
        
        for stage_code, stage_name in stage_names.items():
            if stage_code in self.inventory_data:
                stage_data = self.inventory_data[stage_code]
                total_items = len(stage_data)
                
                # Calculate bottlenecks (stages with low throughput)
                bottleneck_risk = 'High' if total_items < 100 else 'Medium' if total_items < 500 else 'Low'
                
                insights.append({
                    'stage': stage_name,
                    'items_count': total_items,
                    'bottleneck_risk': bottleneck_risk,
                    'efficiency_score': min(100, total_items / 10),  # Simplified efficiency
                    'recommendation': f'Optimize {stage_name} throughput' if bottleneck_risk == 'High' else 'Monitor performance'
                })
                
        return insights

# Initialize analyzer
analyzer = SupplyChainAnalyzer(DATA_PATH)

@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Beverly Knits AI-Enhanced ERP</title>
        <meta charset="utf-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
            .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
            .header { text-align: center; color: white; margin-bottom: 30px; }
            .header h1 { font-size: 2.5em; margin-bottom: 10px; }
            .header p { font-size: 1.2em; opacity: 0.9; }
            
            .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { background: white; border-radius: 12px; padding: 25px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
            .card h2 { color: #2c3e50; margin-bottom: 20px; font-size: 1.4em; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
            
            .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }
            .kpi-item { text-align: center; padding: 15px; background: linear-gradient(135deg, #74b9ff, #0984e3); color: white; border-radius: 8px; }
            .kpi-value { font-size: 1.8em; font-weight: bold; margin-bottom: 5px; }
            .kpi-label { font-size: 0.9em; opacity: 0.9; }
            
            .alert-high { background: linear-gradient(135deg, #ff7675, #d63031); }
            .alert-medium { background: linear-gradient(135deg, #fdcb6e, #e17055); }
            .alert-low { background: linear-gradient(135deg, #55a3ff, #74b9ff); }
            
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th { background: #34495e; color: white; padding: 12px; text-align: left; font-weight: 600; }
            td { padding: 10px; border-bottom: 1px solid #ecf0f1; }
            tr:hover { background: #f8f9fa; }
            
            .recommendation { background: linear-gradient(135deg, #00b894, #00cec9); color: white; padding: 15px; border-radius: 8px; margin: 10px 0; }
            .savings { color: #00b894; font-weight: bold; }
            .cost-reduction { color: #e74c3c; font-weight: bold; }
            
            .status-indicator { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
            .status-running { background: #2ecc71; }
            .status-warning { background: #f39c12; }
            .status-error { background: #e74c3c; }
            
            .loading { text-align: center; color: #7f8c8d; padding: 20px; }
            .refresh-btn { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; margin: 10px 0; }
            .refresh-btn:hover { background: #2980b9; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏭 Beverly Knits AI-Enhanced ERP</h1>
                <p>Supply Chain Intelligence & Optimization Platform</p>
                <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Data</button>
            </div>
            
            <div class="dashboard">
                <!-- KPI Dashboard -->
                <div class="card">
                    <h2>📊 Key Performance Indicators</h2>
                    <div class="kpi-grid" id="kpi-dashboard">
                        <div class="loading">Loading KPIs...</div>
                    </div>
                </div>
                
                <!-- Inventory Optimization -->
                <div class="card">
                    <h2>⚡ Inventory Optimization</h2>
                    <div id="optimization-recommendations">
                        <div class="loading">Calculating EOQ recommendations...</div>
                    </div>
                </div>
                
                <!-- Supplier Analysis -->
                <div class="card">
                    <h2>🏢 Supplier Risk Analysis</h2>
                    <div id="supplier-analysis">
                        <div class="loading">Analyzing supplier performance...</div>
                    </div>
                </div>
                
                <!-- Production Insights -->
                <div class="card">
                    <h2>🔧 Production Pipeline</h2>
                    <div id="production-insights">
                        <div class="loading">Analyzing production stages...</div>
                    </div>
                </div>
                
                <!-- Raw Data Tables -->
                <div class="card">
                    <h2>📋 Yarn Inventory</h2>
                    <table id="yarn-table">
                        <tr><th colspan="4" class="loading">Loading yarn data...</th></tr>
                    </table>
                </div>
                
                <div class="card">
                    <h2>💰 Sales Performance</h2>
                    <table id="sales-table">
                        <tr><th colspan="5" class="loading">Loading sales data...</th></tr>
                    </table>
                </div>
            </div>
        </div>
        
        <script>
            // Load KPIs
            fetch('/api/kpis').then(r => r.json()).then(data => {
                let html = '';
                Object.entries(data).forEach(([key, value]) => {
                    const alertClass = key.includes('alert') ? 'alert-high' : '';
                    html += `<div class="kpi-item ${alertClass}">
                        <div class="kpi-value">${value}</div>
                        <div class="kpi-label">${key.replace(/_/g, ' ').toUpperCase()}</div>
                    </div>`;
                });
                document.getElementById('kpi-dashboard').innerHTML = html;
            });
            
            // Load optimization recommendations
            fetch('/api/optimization').then(r => r.json()).then(data => {
                let html = '<h3>💡 Top Optimization Opportunities</h3>';
                data.recommendations.slice(0, 5).forEach(rec => {
                    html += `<div class="recommendation">
                        <strong>${rec.item}</strong><br>
                        EOQ: ${rec.eoq} units | Current Stock: ${rec.current_stock}<br>
                        <span class="savings">Potential Savings: $${rec.savings_potential.toFixed(0)}</span> | 
                        Action: ${rec.action}
                    </div>`;
                });
                document.getElementById('optimization-recommendations').innerHTML = html;
            });
            
            // Load supplier analysis
            fetch('/api/suppliers').then(r => r.json()).then(data => {
                let html = '<table><tr><th>Supplier</th><th>Value</th><th>Risk</th><th>Items</th></tr>';
                data.suppliers.slice(0, 8).forEach(sup => {
                    const riskColor = sup.risk_level === 'High' ? 'status-error' : 
                                     sup.risk_level === 'Medium' ? 'status-warning' : 'status-running';
                    html += `<tr>
                        <td>${sup.supplier}</td>
                        <td>${sup.total_value}</td>
                        <td><span class="status-indicator ${riskColor}"></span>${sup.risk_level}</td>
                        <td>${sup.item_count} items</td>
                    </tr>`;
                });
                html += '</table>';
                document.getElementById('supplier-analysis').innerHTML = html;
            });
            
            // Load production insights
            fetch('/api/production').then(r => r.json()).then(data => {
                let html = '<table><tr><th>Stage</th><th>Items</th><th>Bottleneck Risk</th><th>Recommendation</th></tr>';
                data.insights.forEach(insight => {
                    const riskColor = insight.bottleneck_risk === 'High' ? 'status-error' : 
                                     insight.bottleneck_risk === 'Medium' ? 'status-warning' : 'status-running';
                    html += `<tr>
                        <td>${insight.stage}</td>
                        <td>${insight.items_count}</td>
                        <td><span class="status-indicator ${riskColor}"></span>${insight.bottleneck_risk}</td>
                        <td>${insight.recommendation}</td>
                    </tr>`;
                });
                html += '</table>';
                document.getElementById('production-insights').innerHTML = html;
            });
            
            // Load yarn inventory
            fetch('/api/yarn').then(r => r.json()).then(data => {
                let table = '<tr><th>Desc#</th><th>Description</th><th>Balance</th><th>Supplier</th></tr>';
                data.yarns.slice(0, 15).forEach(y => {
                    table += `<tr><td>${y.desc_num}</td><td>${y.description}</td><td>${y.balance}</td><td>${y.supplier}</td></tr>`;
                });
                document.getElementById('yarn-table').innerHTML = table;
            });
            
            // Load sales data
            fetch('/api/sales').then(r => r.json()).then(data => {
                let table = '<tr><th>Document</th><th>Customer</th><th>Style</th><th>Qty</th><th>Price</th></tr>';
                data.orders.slice(0, 15).forEach(o => {
                    table += `<tr><td>${o.document}</td><td>${o.customer}</td><td>${o.style}</td><td>${o.qty}</td><td>$${o.price}</td></tr>`;
                });
                document.getElementById('sales-table').innerHTML = table;
            });
        </script>
    </body>
    </html>
    """

@app.route("/api/kpis")
def kpis():
    """Key Performance Indicators endpoint"""
    return jsonify(analyzer.calculate_kpis())

@app.route("/api/optimization")  
def optimization():
    """Inventory optimization recommendations"""
    recommendations = analyzer.get_inventory_optimization()
    return jsonify({"recommendations": recommendations})

@app.route("/api/suppliers")
def suppliers():
    """Supplier analysis and risk assessment"""
    supplier_analysis = analyzer.get_supplier_analysis()
    return jsonify({"suppliers": supplier_analysis})

@app.route("/api/production")
def production():
    """Production pipeline insights"""
    insights = analyzer.get_production_insights()
    return jsonify({"insights": insights})

@app.route("/api/yarn")
def yarn():
    """Yarn inventory data"""
    yarn_file = DATA_PATH / "yarn_inventory (1).xlsx"
    yarns = []
    if yarn_file.exists():
        try:
            df = pd.read_excel(yarn_file)
            for _, row in df.head(20).iterrows():
                yarns.append({
                    "desc_num": str(row.get("Desc#", "")),
                    "description": str(row.get("Description", ""))[:40] + "..." if len(str(row.get("Description", ""))) > 40 else str(row.get("Description", "")),
                    "balance": f"{row.get('Planning Balance', 0):,.0f}",
                    "supplier": str(row.get("Supplier", ""))[:25]
                })
        except Exception as e:
            print(f"Error loading yarn: {e}")
    return jsonify({"yarns": yarns})

@app.route("/api/sales")
def sales():
    """Sales data"""
    sales_file = DATA_PATH / "Sales Activity Report (4).xlsx"
    orders = []
    if sales_file.exists():
        try:
            df = pd.read_excel(sales_file)
            for _, row in df.head(20).iterrows():
                orders.append({
                    "document": str(row.get("Document", "")),
                    "customer": str(row.get("Customer", ""))[:20],
                    "style": str(row.get("Style", "")),
                    "qty": f"{row.get('Qty Shipped', 0):,.0f}",
                    "price": f"{row.get('Unit Price', 0):.2f}"
                })
        except Exception as e:
            print(f"Error loading sales: {e}")
    return jsonify({"orders": orders})

if __name__ == "__main__":
    print(f"Starting Beverly Knits AI-Enhanced ERP on http://localhost:5002")
    print(f"Data path: {DATA_PATH}")
    print(f"Advanced analytics enabled")
    
    # Initialize and validate data
    if DATA_PATH.exists():
        files = list(DATA_PATH.glob("*.*"))
        print(f"Found {len(files)} data files")
        
        # Load and validate key datasets
        kpis = analyzer.calculate_kpis()
        print(f"KPIs calculated: {len(kpis)} metrics")
        
        recommendations = analyzer.get_inventory_optimization()
        print(f"Optimization opportunities: {len(recommendations)}")
        
        suppliers = analyzer.get_supplier_analysis()  
        print(f"Supplier analysis: {len(suppliers)} suppliers")
        
    app.run(host="0.0.0.0", port=5002, debug=False)
