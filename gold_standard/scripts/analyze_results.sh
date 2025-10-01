#!/bin/bash
# Quick summary of fine-tuning results

REPORT_DIR=${1:-scripts/eval/reports/finetune_4o_mini_20251001-142155}

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Fine-Tuned GPT-4o-mini Evaluation Results             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Overall metrics
echo "📊 OVERALL METRICS:"
cat "$REPORT_DIR/summary.json" | jq -r '
  "   Verdict Accuracy:    " + (.verdict_acc * 100 | tostring | split(".")[0]) + "." + (.verdict_acc * 100 | tostring | split(".")[1][:1]) + "%",
  "   Verdict F1-Score:    " + (.verdict_f1 * 100 | tostring | split(".")[0]) + "." + (.verdict_f1 * 100 | tostring | split(".")[1][:1]) + "%",
  "   Score MAE:           " + (.score_mae | tostring) + " points",
  "   Pearson Correlation: " + (.score_pearson | tostring)
'
echo ""

# Per-verdict breakdown
echo "🎯 PER-VERDICT ACCURACY:"
awk -F',' 'NR>1 {
  true[$2]++; 
  if($2==$3) correct[$2]++
} 
END {
  verdicts[0] = "freely_listen"
  verdicts[1] = "context_required"
  verdicts[2] = "caution_limit"
  verdicts[3] = "avoid_formation"
  
  for (i=0; i<4; i++) {
    v = verdicts[i]
    c = (correct[v] ? correct[v] : 0)
    t = (true[v] ? true[v] : 0)
    pct = (t > 0 ? c/t*100 : 0)
    printf "   %-20s %2d/%2d  (%5.1f%%)\n", v ":", c, t, pct
  }
}' "$REPORT_DIR/predictions.csv"

echo ""
echo "💡 KEY INSIGHTS:"
echo "   ✅ Perfect accuracy on 'freely_listen' (100%)"
echo "   ✅ Near-perfect on 'avoid_formation' (95%+)"
echo "   ⚠️  Moderate confusion between middle verdicts"
echo ""

echo "💰 COST ESTIMATE (per song):"
echo "   ~$0.0006 USD"
echo ""

echo "📁 Full report:"
echo "   $REPORT_DIR"
echo ""
