# ERP Data Mapping Guide
## Path: `/mnt/c/Users/psytz/TMUX Final/Agent-MCP/ERP Data/New folder`

### 🔴 CRITICAL YARN SHORTAGES (11 Negative Balance)
**File**: `yarn_inventory (1).xlsx`
| Yarn ID | Balance | Description | Action |
|---------|---------|-------------|--------|
| 19004 | -994.4 | 24/1 96/4 Polyester Black | EMERGENCY |
| 18868 | -494.0 | 30/1 60/40 Recycled Poly | EMERGENCY |
| 18851 | -340.2 | 46/1 100% Nomex Heather | EMERGENCY |
| 18892 | -276.5 | 1/150/48 100% Polyester | URGENT |
| 14270 | -251.8 | 26/1 75/15/10 Modacrylic | URGENT |

### 📊 KEY DATA FILES
1. **Yarn Inventory**: `yarn_inventory (1).xlsx`
   - 1,197 yarn items
   - Columns: Desc#, Description, Supplier, Theoretical Balance, Consumed
   - 529 items < 100 units (critical)
   - 11 items negative (emergency)

2. **Bill of Materials**: `BOM_2(Sheet1).csv`
   - 55,160 product-to-yarn mappings
   - 5,925 unique products
   - 1,632 unique yarns
   - Columns: Style_id, Yarn_ID, BOM_Percent

3. **Sales History**: `Sales Activity Report (4).xlsx`
   - 5,151 transactions
   - May 2024 - July 2025
   - 526 active products
   - Columns: Date, Style, Quantity, Customer

4. **Current Inventory**: `eFab_Inventory_F01_20250808.xlsx`
   - 11,836 SKUs (finished goods)
   - August 8, 2025 snapshot
   - Columns: SKU, Description, Quantity, Location

5. **Production Inventory**: `eFab_Inventory_P01_20250808.xlsx`
   - Work in progress items
   - Production stage tracking

### 🎯 USAGE IN CODE
```python
from pathlib import Path
import pandas as pd

# Standard data path
DATA_PATH = Path("ERP Data/New folder")

# Load critical files
yarn_inv = pd.read_excel(DATA_PATH / "yarn_inventory (1).xlsx")
bom = pd.read_csv(DATA_PATH / "BOM_2(Sheet1).csv")
sales = pd.read_excel(DATA_PATH / "Sales Activity Report (4).xlsx")
current_inv = pd.read_excel(DATA_PATH / "eFab_Inventory_F01_20250808.xlsx")

# Find critical shortages
critical = yarn_inv[yarn_inv['Theoretical Balance'] < 0]
```

### ⚠️ DATA QUALITY NOTES
- All files current as of August 8, 2025
- Some yarns show negative balance (oversold)
- BOM percentages must sum to 100% per product
- Sales data includes returns (negative quantities)
- Inventory stages: G00 → G02 → I01 → F01 → P01

### 📈 AGENT RESPONSIBILITIES
- **SUPPLY CHAIN**: Process negative yarns, BOM explosion
- **INVENTORY**: Dashboard for 11,836 SKUs, multi-stage tracking
- **ML FORECAST**: Train on 5,151 sales records, predict demand

---
*Generated: August 8, 2025 - For use with beverly_comprehensive_erp.py*
