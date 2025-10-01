#!/bin/bash
# Monitor evaluation progress

echo "🔍 Checking evaluation progress..."
echo ""

# Find latest report directory
LATEST_DIR=$(ls -t scripts/eval/reports/finetune_4o_mini_*/  2>/dev/null | head -1 | sed 's/\/$//')

if [ -z "$LATEST_DIR" ]; then
    echo "❌ No evaluation reports found"
    exit 1
fi

echo "📁 Latest report: $LATEST_DIR"
echo ""

# Check if files exist
if [ -f "$LATEST_DIR/all_results.jsonl" ]; then
    PROCESSED=$(wc -l < "$LATEST_DIR/all_results.jsonl" | xargs)
    echo "✅ Songs processed: $PROCESSED / 142"
    echo ""
    
    if [ "$PROCESSED" -eq 142 ]; then
        echo "🎉 Evaluation complete!"
        echo ""
        
        if [ -f "$LATEST_DIR/summary.txt" ]; then
            echo "📊 Summary:"
            cat "$LATEST_DIR/summary.txt"
        fi
    else
        echo "⏳ Still processing... (~$((142 - PROCESSED)) songs remaining)"
    fi
else
    echo "⏳ Evaluation in progress (no results file yet)"
    echo ""
    echo "   This is normal - results are written at the end."
    echo "   Check back in a few minutes."
fi

echo ""
echo "To monitor continuously, run:"
echo "  watch -n 10 ./scripts/eval/check_eval_progress.sh"

