#!/bin/bash
# Continuous Code Quality Monitor for Manufacturing ERP

MONITOR_FILE="/mnt/c/Users/psytz/TMUX Final/Agent-MCP/beverly_comprehensive_erp.py"
QUALITY_SCRIPT="/mnt/c/Users/psytz/TMUX Final/Agent-MCP/code_quality_monitor.py"
LOG_FILE="/mnt/c/Users/psytz/TMUX Final/Agent-MCP/quality_monitor.log"

echo "🔍 Starting Continuous Code Quality Monitoring"
echo "📁 Monitoring: $MONITOR_FILE"
echo "⏰ Check interval: 5 minutes"
echo "=" >> $LOG_FILE
echo "Started: $(date)" >> $LOG_FILE

while true; do
    # Get current file hash
    CURRENT_HASH=$(md5sum "$MONITOR_FILE" | cut -d' ' -f1)
    
    # Check if file changed
    if [ "$LAST_HASH" != "$CURRENT_HASH" ]; then
        echo "[$(date)] File changed, running quality check..." | tee -a $LOG_FILE
        
        # Run quality analysis
        python3 "$QUALITY_SCRIPT" 2>&1 | tee -a $LOG_FILE
        
        # Extract score
        SCORE=$(python3 "$QUALITY_SCRIPT" 2>&1 | grep "QUALITY SCORE:" | sed 's/.*: \([0-9]*\).*/\1/')
        
        # Alert if score is low
        if [ "$SCORE" -lt "60" ]; then
            echo "⚠️  WARNING: Quality score is $SCORE/100 - Immediate action required!" | tee -a $LOG_FILE
        elif [ "$SCORE" -lt "80" ]; then
            echo "📊 Quality score: $SCORE/100 - Improvements needed" | tee -a $LOG_FILE
        else
            echo "✅ Quality score: $SCORE/100 - Good quality maintained" | tee -a $LOG_FILE
        fi
        
        LAST_HASH=$CURRENT_HASH
    fi
    
    # Wait 5 minutes
    sleep 300
done