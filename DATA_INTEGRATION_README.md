cp,# Beverly Knits Data Integration System

## Overview

This comprehensive data integration system maps and integrates all 10 CSV files for the Beverly Knits raw material planning system. The integration handles complex relationships between sales orders, product specifications (BOMs), yarn inventory, supplier constraints, and demand forecasting.

## Data Files and Their Roles

### 1. **Sales Data**
- `eFab_SO_List.csv` - Active sales orders with quantities and ship dates
- `Sales Activity Report.csv` - Historical sales transactions for trend analysis


### 2. **Product Data**
- `Style_BOM.csv` - Bill of Materials defining yarn composition for each style
- Links styles to their component yarns with percentages

### 3. **Yarn Data**
- `Yarn_ID.csv` - Master yarn specifications and attributes
- `Yarn_ID_1.csv` - Additional yarn master data
- `Yarn_ID_Current_Inventory.csv` - Current inventory levels and costs

### 4. **Inventory Data**
- `inventory.csv` - Simplified inventory for system upload
- `Yarn_Demand_2025-06-27_0442.csv` - Time-phased demand and supply

### 5. **Demand Data**
- `cfab_Yarn_Demand_By_Style.csv` - Yarn requirements by style and week

### 6. **Supplier Data**
- `Supplier_ID.csv` - Supplier constraints (lead times, MOQs, type)

## Key Data Relationships

```
Sales Orders (eFab_SO_List)
    ↓ [Style_ID]
Style BOM (Style_BOM)
    ↓ [Yarn_ID]
Yarn Master (Yarn_ID) ← → Yarn Inventory
    ↓ [Supplier]
Supplier Master (Supplier_ID)
```

## Integration Architecture

### 1. **Data Layer**
- Loads and validates all CSV files
- Handles data quality issues (nulls, "Remove" values, formatting)
- Standardizes IDs across files

### 2. **Integration Layer**
- Creates unified yarn master combining all yarn sources
- Calculates total demand through BOM explosion
- Performs inventory netting
- Applies business rules (safety stock, MOQs)

### 3. **Output Layer**
- Generates procurement recommendations
- Provides urgency classifications
- Creates time-phased planning views

## Usage

### Basic Integration
```python
from beverly_knits_data_integration import BeverlyKnitsDataIntegrator

# Initialize integrator
integrator = BeverlyKnitsDataIntegrator(data_path="data/")

# Run complete integration
integrated_data = integrator.run_full_integration()
```

### Run Complete Planning System
```bash
python main_planning_system.py
```

### Test Data Integration
```bash
python test_data_integration.py
```

### Generate Visualizations
```bash
python create_data_visualizations.py
```

## Output Files

The system generates several integrated output files:

1. **integrated_yarn_master.csv** - Complete yarn information with inventory and supplier data
2. **total_yarn_demand.csv** - Aggregated demand from all sources
3. **net_requirements.csv** - Net requirements after inventory netting
4. **procurement_plan.csv** - Final purchase recommendations with urgency
5. **weekly_demand_analysis.csv** - Time-phased demand breakdown

## Key Features

### Data Quality Handling
- Removes invalid "Remove" entries in supplier data
- Handles multiple date formats
- Manages negative inventory values
- Validates BOM percentages sum to 100%

### Business Logic Implementation
- **Safety Stock**: 20% buffer on all demands
- **MOQ Compliance**: Rounds up to supplier minimum order quantities
- **Lead Time Analysis**: Calculates urgency based on need date vs lead time
- **Cost Optimization**: Considers unit costs in procurement decisions

### Integration Validations
- Verifies all style-yarn relationships
- Checks supplier-yarn linkages
- Validates calculation accuracy
- Ensures data consistency across sources

## Data Flow Example

1. **Sales Order**: 100 yards of style "125792/1" needed
2. **BOM Lookup**: Style requires 91.4% of Yarn 18767, 8.6% of Yarn 18929
3. **Demand Calculation**: 91.4 lbs of 18767, 8.6 lbs of 18929 needed
4. **Inventory Check**: Current inventory and on-order quantities
5. **Net Requirement**: Demand - Available Supply
6. **Safety Stock**: Add 20% buffer
7. **MOQ Application**: Round up to supplier minimums
8. **Procurement Plan**: Generate purchase orders with urgency flags

## Testing

The system includes comprehensive testing:
- Data loading validation
- Key relationship integrity
- Calculation accuracy
- Business rule compliance
- Data quality checks

Run tests with: `python test_data_integration.py`

## Troubleshooting

### Common Issues
1. **Missing Yarn in Master**: Some yarns in BOM may not have master data
2. **Supplier Mismatches**: Yarn suppliers may not match supplier master exactly
3. **Date Parsing**: Various date formats need standardization
4. **Negative Inventory**: Some yarns show negative planning balances

### Solutions
- The system handles these gracefully with warnings
- Missing data is logged but doesn't stop processing
- Default values are applied where necessary

## Future Enhancements

1. **Real-time Integration**: Connect to live ERP systems
2. **Demand Forecasting**: Add ML-based demand prediction
3. **Multi-scenario Planning**: Support what-if analysis
4. **Supplier Performance**: Track and score supplier reliability
5. **Cost Optimization**: Advanced algorithms for order consolidation

## Support

For questions or issues with the data integration:
1. Check test_results.csv for validation failures
2. Review data_quality_report.csv for data issues
3. Examine planning_summary_report.txt for insights
4. Verify all CSV files are in the correct format