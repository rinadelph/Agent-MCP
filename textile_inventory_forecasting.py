"""
Textile Inventory Forecasting and Yarn Requirement System
Analyzes historical sales, forecasts demand, monitors inventory, and calculates yarn requirements
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Data paths
DATA_DIR = Path("/mnt/c/Users/psytz/TMUX Final/Agent-MCP/ERP Data/New folder")

class TextileInventoryForecaster:
    """Main system for textile inventory forecasting and yarn requirement calculation"""
    
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = Path(data_dir)
        self.sales_data = None
        self.bom_data = None
        self.yarn_inventory = None
        self.fabric_inventory = None
        self.forecast_results = {}
        
    def load_data(self):
        """Load all ERP data files"""
        print("Loading ERP data files...")
        
        # Load BOM data
        bom_path = self.data_dir / "BOM_2(Sheet1).csv"
        if bom_path.exists():
            self.bom_data = pd.read_csv(bom_path)
            print(f"✓ Loaded BOM data: {len(self.bom_data)} records")
        
        # Load sales data
        sales_path = self.data_dir / "Sales Activity Report (4).xlsx"
        if sales_path.exists():
            self.sales_data = pd.read_excel(sales_path)
            self.sales_data['Invoice Date'] = pd.to_datetime(self.sales_data['Invoice Date'])
            print(f"✓ Loaded sales data: {len(self.sales_data)} records")
        
        # Load yarn inventory
        yarn_inv_path = self.data_dir / "Yarn_Inventory_.xlsx"
        if yarn_inv_path.exists():
            self.yarn_inventory = pd.read_excel(yarn_inv_path)
            print(f"✓ Loaded yarn inventory: {len(self.yarn_inventory)} items")
        
        # Load fabric inventory (multiple files)
        fabric_files = list(self.data_dir.glob("eFab_Inventory_*.xlsx"))
        if fabric_files:
            fabric_dfs = []
            for file in fabric_files:
                df = pd.read_excel(file)
                df['source_file'] = file.stem
                fabric_dfs.append(df)
            self.fabric_inventory = pd.concat(fabric_dfs, ignore_index=True)
            print(f"✓ Loaded fabric inventory from {len(fabric_files)} files: {len(self.fabric_inventory)} records")
    
    def analyze_sales_history(self):
        """Analyze historical sales patterns"""
        if self.sales_data is None:
            print("No sales data loaded")
            return None
        
        print("\n=== Sales History Analysis ===")
        
        # Group by style and calculate statistics
        style_summary = self.sales_data.groupby('Style').agg({
            'Qty Shipped': ['sum', 'mean', 'std', 'count'],
            'Line Price': 'sum',
            'Invoice Date': ['min', 'max']
        }).round(2)
        
        # Flatten column names
        style_summary.columns = ['_'.join(col).strip() for col in style_summary.columns]
        style_summary = style_summary.rename(columns={
            'Qty Shipped_sum': 'Total_Qty',
            'Qty Shipped_mean': 'Avg_Qty_Per_Order',
            'Qty Shipped_std': 'Std_Dev',
            'Qty Shipped_count': 'Order_Count',
            'Line Price_sum': 'Total_Revenue',
            'Invoice Date_min': 'First_Sale',
            'Invoice Date_max': 'Last_Sale'
        })
        
        # Calculate days active
        style_summary['Days_Active'] = (
            style_summary['Last_Sale'] - style_summary['First_Sale']
        ).dt.days
        
        # Calculate average daily demand
        style_summary['Avg_Daily_Demand'] = (
            style_summary['Total_Qty'] / style_summary['Days_Active']
        ).replace([np.inf, -np.inf], 0).fillna(0).round(2)
        
        # Sort by total quantity
        style_summary = style_summary.sort_values('Total_Qty', ascending=False)
        
        print(f"Total unique styles: {len(style_summary)}")
        print(f"Total quantity shipped: {style_summary['Total_Qty'].sum():,.0f}")
        print(f"Total revenue: ${style_summary['Total_Revenue'].sum():,.2f}")
        
        return style_summary
    
    def forecast_demand(self, style_summary, forecast_days=90):
        """Simple demand forecasting based on historical averages"""
        print(f"\n=== Demand Forecast ({forecast_days} days) ===")
        
        forecast = pd.DataFrame()
        forecast['Style'] = style_summary.index
        forecast['Historical_Daily_Avg'] = style_summary['Avg_Daily_Demand'].values
        
        # Apply simple growth factor (can be enhanced with ML models)
        # Using moving average trend
        forecast['Growth_Factor'] = 1.0  # Default no growth
        
        # Calculate forecast
        forecast['Forecasted_Demand'] = (
            forecast['Historical_Daily_Avg'] * 
            forecast['Growth_Factor'] * 
            forecast_days
        ).round(0)
        
        # Add confidence intervals (simplified)
        forecast['Lower_Bound'] = (forecast['Forecasted_Demand'] * 0.8).round(0)
        forecast['Upper_Bound'] = (forecast['Forecasted_Demand'] * 1.2).round(0)
        
        # Store results
        self.forecast_results = forecast
        
        print(f"Total forecasted demand: {forecast['Forecasted_Demand'].sum():,.0f} units")
        print(f"Top 10 styles by forecasted demand:")
        print(forecast.nlargest(10, 'Forecasted_Demand')[['Style', 'Forecasted_Demand']])
        
        return forecast
    
    def identify_stockout_risks(self):
        """Identify products at risk of stockout"""
        print("\n=== Stockout Risk Analysis ===")
        
        if self.fabric_inventory is None or self.forecast_results.empty:
            print("Missing required data for stockout analysis")
            return None
        
        # Aggregate fabric inventory by style (simplified - would need proper mapping)
        current_inventory = self.fabric_inventory.groupby('Customer')['Qty (yds)'].sum().reset_index()
        current_inventory.columns = ['Style', 'Current_Stock']
        
        # Merge with forecast
        risk_analysis = self.forecast_results.merge(
            current_inventory, 
            on='Style', 
            how='left'
        )
        risk_analysis['Current_Stock'] = risk_analysis['Current_Stock'].fillna(0)
        
        # Calculate days of supply
        risk_analysis['Days_of_Supply'] = (
            risk_analysis['Current_Stock'] / 
            risk_analysis['Historical_Daily_Avg']
        ).replace([np.inf, -np.inf], 999).fillna(999).round(0)
        
        # Determine risk level
        def assign_risk(days):
            if days < 7:
                return 'CRITICAL'
            elif days < 14:
                return 'HIGH'
            elif days < 30:
                return 'MEDIUM'
            else:
                return 'LOW'
        
        risk_analysis['Risk_Level'] = risk_analysis['Days_of_Supply'].apply(assign_risk)
        
        # Calculate shortage
        risk_analysis['Shortage'] = (
            risk_analysis['Forecasted_Demand'] - risk_analysis['Current_Stock']
        ).clip(lower=0)
        
        # Summary
        risk_summary = risk_analysis['Risk_Level'].value_counts()
        print("\nRisk Level Distribution:")
        for level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = risk_summary.get(level, 0)
            print(f"  {level}: {count} styles")
        
        # Show critical items
        critical = risk_analysis[risk_analysis['Risk_Level'] == 'CRITICAL']
        if not critical.empty:
            print("\nCRITICAL stockout risks:")
            print(critical[['Style', 'Current_Stock', 'Forecasted_Demand', 'Days_of_Supply']].head(10))
        
        return risk_analysis
    
    def calculate_yarn_requirements(self, production_plan=None):
        """Calculate yarn requirements based on production plan"""
        print("\n=== Yarn Requirement Calculation ===")
        
        if self.bom_data is None:
            print("No BOM data loaded")
            return None
        
        # If no production plan provided, use forecast as production plan
        if production_plan is None and not self.forecast_results.empty:
            production_plan = self.forecast_results[['Style', 'Forecasted_Demand']]
            production_plan.columns = ['Style', 'Quantity']
        
        # Merge production plan with BOM
        yarn_requirements = {}
        
        for _, row in production_plan.iterrows():
            style = row['Style']
            quantity = row['Quantity']
            
            # Find BOM entries for this style
            style_bom = self.bom_data[self.bom_data['Style_id'].str.contains(str(style), na=False)]
            
            for _, bom_row in style_bom.iterrows():
                yarn_id = bom_row['Yarn_ID']
                if pd.notna(yarn_id):
                    bom_percent = bom_row['BOM_Percent']
                    unit = bom_row['unit']
                    
                    # Calculate requirement
                    requirement = quantity * bom_percent
                    
                    if yarn_id not in yarn_requirements:
                        yarn_requirements[yarn_id] = {
                            'total_required': 0,
                            'unit': unit,
                            'styles': []
                        }
                    
                    yarn_requirements[yarn_id]['total_required'] += requirement
                    yarn_requirements[yarn_id]['styles'].append({
                        'style': style,
                        'quantity': quantity,
                        'requirement': requirement
                    })
        
        # Convert to DataFrame
        yarn_req_df = pd.DataFrame([
            {
                'Yarn_ID': yarn_id,
                'Total_Required': data['total_required'],
                'Unit': data['unit'],
                'Num_Styles': len(data['styles'])
            }
            for yarn_id, data in yarn_requirements.items()
        ])
        
        if not yarn_req_df.empty:
            yarn_req_df = yarn_req_df.sort_values('Total_Required', ascending=False)
            print(f"Total unique yarns required: {len(yarn_req_df)}")
            print(f"Top 10 yarn requirements:")
            print(yarn_req_df.head(10))
        else:
            print("No yarn requirements calculated")
        
        return yarn_req_df
    
    def analyze_yarn_shortages(self, yarn_requirements):
        """Compare yarn requirements against inventory"""
        print("\n=== Yarn Shortage Analysis ===")
        
        if self.yarn_inventory is None or yarn_requirements is None:
            print("Missing required data for shortage analysis")
            return None
        
        # Prepare yarn inventory data
        yarn_inv = self.yarn_inventory[['Desc#', 'Theoretical Balance', 'On Order', 'Allocated']]
        yarn_inv['Available'] = yarn_inv['Theoretical Balance'] - yarn_inv['Allocated']
        yarn_inv = yarn_inv.rename(columns={'Desc#': 'Yarn_ID'})
        
        # Merge with requirements
        shortage_analysis = yarn_requirements.merge(
            yarn_inv,
            on='Yarn_ID',
            how='left'
        )
        
        shortage_analysis['Available'] = shortage_analysis['Available'].fillna(0)
        shortage_analysis['On Order'] = shortage_analysis['On Order'].fillna(0)
        
        # Calculate shortage
        shortage_analysis['Shortage'] = (
            shortage_analysis['Total_Required'] - 
            shortage_analysis['Available'] - 
            shortage_analysis['On Order']
        ).clip(lower=0)
        
        # Determine status
        def assign_status(row):
            if row['Shortage'] > row['Available']:
                return 'CRITICAL_SHORTAGE'
            elif row['Shortage'] > 0:
                return 'SHORTAGE_PREDICTED'
            elif row['Available'] < row['Total_Required'] * 1.5:
                return 'LOW_STOCK'
            else:
                return 'ADEQUATE'
        
        shortage_analysis['Status'] = shortage_analysis.apply(assign_status, axis=1)
        
        # Summary
        status_summary = shortage_analysis['Status'].value_counts()
        print("\nYarn Status Distribution:")
        for status in ['CRITICAL_SHORTAGE', 'SHORTAGE_PREDICTED', 'LOW_STOCK', 'ADEQUATE']:
            count = status_summary.get(status, 0)
            print(f"  {status}: {count} yarns")
        
        # Show critical shortages
        critical = shortage_analysis[shortage_analysis['Status'] == 'CRITICAL_SHORTAGE']
        if not critical.empty:
            print("\nCRITICAL yarn shortages:")
            print(critical[['Yarn_ID', 'Total_Required', 'Available', 'Shortage']].head(10))
        
        return shortage_analysis
    
    def generate_report(self):
        """Generate comprehensive analysis report"""
        print("\n" + "="*60)
        print("COMPREHENSIVE INVENTORY ANALYSIS REPORT")
        print("="*60)
        print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Load all data
        self.load_data()
        
        # Run analysis pipeline
        style_summary = self.analyze_sales_history()
        
        if style_summary is not None:
            forecast = self.forecast_demand(style_summary)
            risk_analysis = self.identify_stockout_risks()
            yarn_requirements = self.calculate_yarn_requirements()
            
            if yarn_requirements is not None:
                yarn_shortages = self.analyze_yarn_shortages(yarn_requirements)
                
                # Save results to Excel
                output_file = f"inventory_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                with pd.ExcelWriter(output_file) as writer:
                    style_summary.to_excel(writer, sheet_name='Sales_Summary')
                    forecast.to_excel(writer, sheet_name='Demand_Forecast', index=False)
                    if risk_analysis is not None:
                        risk_analysis.to_excel(writer, sheet_name='Stockout_Risk', index=False)
                    yarn_requirements.to_excel(writer, sheet_name='Yarn_Requirements', index=False)
                    if yarn_shortages is not None:
                        yarn_shortages.to_excel(writer, sheet_name='Yarn_Shortages', index=False)
                
                print(f"\n✓ Report saved to: {output_file}")
        
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)

def main():
    """Main execution function"""
    forecaster = TextileInventoryForecaster()
    forecaster.generate_report()

if __name__ == "__main__":
    main()