#!/usr/bin/env python3
"""
Analyze and compare F01 inventory files to determine best data source
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

DATA_PATH = Path("ERP Data/New folder")

def analyze_f01_files():
    """Compare both F01 inventory files and analyze finished goods"""
    
    print("=" * 80)
    print("F01 FINISHED GOODS INVENTORY ANALYSIS")
    print("=" * 80)
    
    # Define file paths
    file_aug4 = DATA_PATH / "eFab_Inventory_F01_20250804 (1).xlsx"
    file_aug8 = DATA_PATH / "eFab_Inventory_F01_20250808.xlsx"
    
    # Load and analyze both files
    files_info = {}
    
    # Analyze Aug 4 file
    if file_aug4.exists():
        try:
            df_aug4 = pd.read_excel(file_aug4)
            files_info['aug4'] = {
                'df': df_aug4,
                'rows': len(df_aug4),
                'columns': len(df_aug4.columns),
                'column_names': list(df_aug4.columns),
                'date': 'Aug 4, 2025',
                'size': '732KB',
                'non_null_counts': df_aug4.count().to_dict(),
                'data_quality': calculate_data_quality(df_aug4)
            }
            print(f"\n✅ Loaded Aug 4 file: {files_info['aug4']['rows']} rows, {files_info['aug4']['columns']} columns")
        except Exception as e:
            print(f"❌ Error loading Aug 4 file: {e}")
    
    # Analyze Aug 8 file
    if file_aug8.exists():
        try:
            df_aug8 = pd.read_excel(file_aug8)
            files_info['aug8'] = {
                'df': df_aug8,
                'rows': len(df_aug8),
                'columns': len(df_aug8.columns),
                'column_names': list(df_aug8.columns),
                'date': 'Aug 8, 2025',
                'size': '720KB',
                'non_null_counts': df_aug8.count().to_dict(),
                'data_quality': calculate_data_quality(df_aug8)
            }
            print(f"✅ Loaded Aug 8 file: {files_info['aug8']['rows']} rows, {files_info['aug8']['columns']} columns")
        except Exception as e:
            print(f"❌ Error loading Aug 8 file: {e}")
    
    # Compare files
    print("\n" + "=" * 80)
    print("FILE COMPARISON")
    print("=" * 80)
    
    if 'aug4' in files_info and 'aug8' in files_info:
        print(f"\n📊 METRICS COMPARISON:")
        print(f"{'Metric':<25} {'Aug 4 File':<20} {'Aug 8 File':<20}")
        print("-" * 65)
        print(f"{'File Size':<25} {files_info['aug4']['size']:<20} {files_info['aug8']['size']:<20}")
        print(f"{'Total Rows':<25} {files_info['aug4']['rows']:<20} {files_info['aug8']['rows']:<20}")
        print(f"{'Total Columns':<25} {files_info['aug4']['columns']:<20} {files_info['aug8']['columns']:<20}")
        print(f"{'Data Quality Score':<25} {files_info['aug4']['data_quality']:.1f}%{'':<15} {files_info['aug8']['data_quality']:.1f}%")
        
        # Find common columns
        cols_aug4 = set(files_info['aug4']['column_names'])
        cols_aug8 = set(files_info['aug8']['column_names'])
        common_cols = cols_aug4.intersection(cols_aug8)
        unique_aug4 = cols_aug4 - cols_aug8
        unique_aug8 = cols_aug8 - cols_aug4
        
        print(f"\n📋 COLUMN ANALYSIS:")
        print(f"  Common columns: {len(common_cols)}")
        print(f"  Unique to Aug 4: {len(unique_aug4)}")
        print(f"  Unique to Aug 8: {len(unique_aug8)}")
        
        if unique_aug4:
            print(f"\n  Aug 4 unique columns: {list(unique_aug4)[:5]}")
        if unique_aug8:
            print(f"  Aug 8 unique columns: {list(unique_aug8)[:5]}")
    
    # Determine best file
    best_file = determine_best_file(files_info)
    
    # Analyze the best file in detail
    if best_file:
        print("\n" + "=" * 80)
        print(f"DETAILED ANALYSIS OF {best_file['date']} FILE (SELECTED AS BEST)")
        print("=" * 80)
        
        df = best_file['df']
        
        # Identify key columns for inventory analysis
        inventory_cols = identify_inventory_columns(df)
        
        if inventory_cols['quantity_col']:
            # Analyze inventory levels
            quantity_col = inventory_cols['quantity_col']
            
            # Remove any non-numeric values
            df[quantity_col] = pd.to_numeric(df[quantity_col], errors='coerce').fillna(0)
            
            total_units = df[quantity_col].sum()
            zero_stock = len(df[df[quantity_col] == 0])
            low_stock = len(df[(df[quantity_col] > 0) & (df[quantity_col] < 10)])
            normal_stock = len(df[(df[quantity_col] >= 10) & (df[quantity_col] < 100)])
            high_stock = len(df[df[quantity_col] >= 100])
            
            print(f"\n📦 INVENTORY DISTRIBUTION:")
            print(f"  Total SKUs: {len(df):,}")
            print(f"  Total Units: {total_units:,.0f}")
            print(f"\n  Stock Levels:")
            print(f"    • Zero Stock: {zero_stock:,} SKUs ({zero_stock/len(df)*100:.1f}%)")
            print(f"    • Low Stock (1-9): {low_stock:,} SKUs ({low_stock/len(df)*100:.1f}%)")
            print(f"    • Normal Stock (10-99): {normal_stock:,} SKUs ({normal_stock/len(df)*100:.1f}%)")
            print(f"    • High Stock (100+): {high_stock:,} SKUs ({high_stock/len(df)*100:.1f}%)")
            
            # Find critical items
            critical_items = df[df[quantity_col] == 0]
            if len(critical_items) > 0 and inventory_cols['description_col']:
                print(f"\n🚨 SAMPLE ZERO-STOCK ITEMS:")
                desc_col = inventory_cols['description_col']
                for i, row in critical_items.head(10).iterrows():
                    item_desc = str(row[desc_col])[:60] if desc_col in row.index else f"Item {i}"
                    print(f"  • {item_desc}")
            
            # Analyze by category if available
            if inventory_cols['category_col']:
                cat_col = inventory_cols['category_col']
                category_analysis = df.groupby(cat_col)[quantity_col].agg(['count', 'sum', 'mean'])
                category_analysis = category_analysis.sort_values('sum', ascending=False)
                
                print(f"\n📊 TOP CATEGORIES BY INVENTORY:")
                print(f"{'Category':<30} {'SKUs':<10} {'Total Units':<15} {'Avg Units':<10}")
                print("-" * 65)
                for cat, row in category_analysis.head(10).iterrows():
                    print(f"{str(cat)[:30]:<30} {int(row['count']):<10} {row['sum']:>14,.0f} {row['mean']:>9,.1f}")
        
        # Generate actionable insights
        print("\n" + "=" * 80)
        print("ACTIONABLE INSIGHTS")
        print("=" * 80)
        
        print("\n✅ RECOMMENDATIONS:")
        print("1. IMMEDIATE ACTIONS:")
        if zero_stock > 0:
            print(f"   • Review {zero_stock:,} zero-stock SKUs for discontinuation or restocking")
        if low_stock > 0:
            print(f"   • Urgent reorder needed for {low_stock:,} low-stock items")
        
        print("\n2. INVENTORY OPTIMIZATION:")
        print(f"   • {high_stock:,} SKUs may be overstocked - review for markdown")
        print(f"   • Consider ABC analysis on {len(df):,} total SKUs")
        
        print("\n3. DATA QUALITY:")
        print(f"   • Data quality score: {best_file['data_quality']:.1f}%")
        if best_file['data_quality'] < 80:
            print("   • Recommend data cleanup before major decisions")
        
        return best_file['df'], inventory_cols
    
    return None, None


def calculate_data_quality(df):
    """Calculate data quality score (0-100)"""
    if df.empty:
        return 0
    
    # Calculate completeness score
    total_cells = df.shape[0] * df.shape[1]
    non_null_cells = df.count().sum()
    completeness = (non_null_cells / total_cells * 100) if total_cells > 0 else 0
    
    return completeness


def identify_inventory_columns(df):
    """Identify key columns for inventory analysis"""
    cols = {
        'quantity_col': None,
        'description_col': None,
        'sku_col': None,
        'category_col': None,
        'location_col': None
    }
    
    # Quantity column patterns
    quantity_patterns = ['Quantity', 'Qty', 'Stock', 'Balance', 'On Hand', 'OnHand', 'Units']
    for col in df.columns:
        for pattern in quantity_patterns:
            if pattern.lower() in col.lower():
                cols['quantity_col'] = col
                break
    
    # Description column patterns
    desc_patterns = ['Description', 'Desc', 'Name', 'Item', 'Product']
    for col in df.columns:
        for pattern in desc_patterns:
            if pattern.lower() in col.lower():
                cols['description_col'] = col
                break
    
    # SKU column patterns
    sku_patterns = ['SKU', 'Code', 'Item Code', 'Product Code', 'ID']
    for col in df.columns:
        for pattern in sku_patterns:
            if pattern.lower() in col.lower():
                cols['sku_col'] = col
                break
    
    # Category column patterns
    cat_patterns = ['Category', 'Cat', 'Type', 'Class', 'Group', 'Department']
    for col in df.columns:
        for pattern in cat_patterns:
            if pattern.lower() in col.lower():
                cols['category_col'] = col
                break
    
    # Location column patterns
    loc_patterns = ['Location', 'Loc', 'Warehouse', 'Bin', 'Zone']
    for col in df.columns:
        for pattern in loc_patterns:
            if pattern.lower() in col.lower():
                cols['location_col'] = col
                break
    
    print(f"\n🔍 IDENTIFIED COLUMNS:")
    for key, value in cols.items():
        if value:
            print(f"  {key}: {value}")
    
    return cols


def determine_best_file(files_info):
    """Determine which file has better data structure"""
    if not files_info:
        return None
    
    scores = {}
    
    for key, info in files_info.items():
        score = 0
        
        # More rows is better
        score += info['rows'] / 100
        
        # Better data quality
        score += info['data_quality']
        
        # More columns might mean more detail
        score += info['columns'] * 2
        
        scores[key] = score
    
    best_key = max(scores, key=scores.get)
    
    print(f"\n✅ SELECTED: {files_info[best_key]['date']} file (Score: {scores[best_key]:.1f})")
    print(f"   Reason: Better data quality and structure")
    
    return files_info[best_key]


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("BEVERLY KNITS - F01 FINISHED GOODS INVENTORY ANALYSIS")
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        df, cols = analyze_f01_files()
        
        if df is not None:
            print("\n✅ Analysis complete - data ready for dashboard integration")
            
            # Save summary to file
            summary_file = DATA_PATH / "f01_inventory_summary.txt"
            with open(summary_file, 'w') as f:
                f.write(f"F01 Inventory Analysis Summary\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write(f"Total SKUs: {len(df)}\n")
                if cols['quantity_col']:
                    f.write(f"Total Units: {df[cols['quantity_col']].sum():,.0f}\n")
            
            print(f"📄 Summary saved to: {summary_file}")
        else:
            print("\n❌ Analysis failed - check file paths and data")
            
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()