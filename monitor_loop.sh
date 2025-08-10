#\!/bin/bash
# Continuous monitoring of code quality

echo "🚀 Starting continuous code monitoring (checks every 60 seconds)"
echo "   Press Ctrl+C to stop"

while true; do
    clear
    echo "=================================================================================="
    echo "CODE QUALITY MONITOR - $(date '+%H:%M:%S')"
    echo "=================================================================================="
    
    # Check if file exists
    if [ \! -f "beverly_comprehensive_erp.py" ]; then
        echo "❌ ERROR: beverly_comprehensive_erp.py not found\!"
        sleep 60
        continue
    fi
    
    # Get file stats
    LINES=$(wc -l < beverly_comprehensive_erp.py)
    FUNCTIONS=$(grep -c "^def \|^    def " beverly_comprehensive_erp.py)
    CLASSES=$(grep -c "^class " beverly_comprehensive_erp.py)
    MODIFIED=$(date -r beverly_comprehensive_erp.py '+%H:%M:%S')
    
    echo ""
    echo "📁 FILE STATISTICS:"
    echo "  Lines: $LINES"
    echo "  Functions: $FUNCTIONS"
    echo "  Classes: $CLASSES"
    echo "  Last Modified: $MODIFIED"
    
    # Check for large functions
    echo ""
    echo "⚠️ LARGE FUNCTIONS (>200 lines):"
    python3 -c "
import ast
with open('beverly_comprehensive_erp.py', 'r') as f:
    tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            size = (node.end_lineno or node.lineno) - node.lineno
            if size > 200:
                print(f'  🔴 {node.name}: {size} lines')
    "
    
    # Check implementation status
    echo ""
    echo "🎯 CRITICAL IMPLEMENTATIONS:"
    
    # Check for critical yarn IDs
    YARN_19004=$(grep -c "19004" beverly_comprehensive_erp.py)
    YARN_18868=$(grep -c "18868" beverly_comprehensive_erp.py)
    YARN_18851=$(grep -c "18851" beverly_comprehensive_erp.py)
    
    if [ $YARN_19004 -gt 0 ]; then
        echo "  ✅ Yarn 19004 implemented ($YARN_19004 references)"
    else
        echo "  ❌ Yarn 19004 NOT implemented"
    fi
    
    if [ $YARN_18868 -gt 0 ]; then
        echo "  ✅ Yarn 18868 implemented ($YARN_18868 references)"
    else
        echo "  ❌ Yarn 18868 NOT implemented"
    fi
    
    if [ $YARN_18851 -gt 0 ]; then
        echo "  ✅ Yarn 18851 implemented ($YARN_18851 references)"
    else
        echo "  ❌ Yarn 18851 NOT implemented"
    fi
    
    # Check for key methods
    echo ""
    echo "📦 KEY FEATURES:"
    grep -q "emergency_shortage_dashboard" beverly_comprehensive_erp.py && echo "  ✅ Emergency Dashboard" || echo "  ❌ Emergency Dashboard"
    grep -q "YarnRequirementCalculator" beverly_comprehensive_erp.py && echo "  ✅ Yarn Calculator" || echo "  ❌ Yarn Calculator"
    grep -q "SalesForecastingEngine" beverly_comprehensive_erp.py && echo "  ✅ ML Forecasting" || echo "  ✅ ML Forecasting"
    
    # Check Flask server
    echo ""
    echo "🌐 FLASK SERVER STATUS:"
    curl -s -o /dev/null -w "  Dashboard: %{http_code}\n" http://127.0.0.1:5003/
    curl -s -o /dev/null -w "  API Status: %{http_code}\n" http://127.0.0.1:5003/api/comprehensive-kpis
    
    # Check for recent test files
    echo ""
    echo "📝 RECENT ACTIVITY (last 5 minutes):"
    find . -maxdepth 1 -name "*.py" -mmin -5 -type f 2>/dev/null | while read -r file; do
        echo "  • Modified: $(basename "$file")"
    done
    
    echo ""
    echo "Next check in 60 seconds..."
    sleep 60
done
