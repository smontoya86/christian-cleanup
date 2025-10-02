#!/bin/bash
# Simple load test using curl for systems without test data

URL="${1:-http://localhost:5001/api/health}"
WORKERS="${2:-10}"
REQUESTS="${3:-50}"

echo "🧪 Simple Load Test"
echo "===================="
echo "URL: $URL"
echo "Workers: $WORKERS"
echo "Requests: $REQUESTS"
echo ""

# Create a temporary directory for results
TMPDIR=$(mktemp -d)
START=$(date +%s.%N)

# Run concurrent requests
for i in $(seq 1 $REQUESTS); do
    (
        WORKER_START=$(date +%s.%N)
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL" 2>&1)
        WORKER_END=$(date +%s.%N)
        ELAPSED=$(echo "$WORKER_END - $WORKER_START" | bc)
        echo "$HTTP_CODE $ELAPSED" >> "$TMPDIR/results.txt"
    ) &
    
    # Limit concurrent workers
    if [ $((i % WORKERS)) -eq 0 ]; then
        wait
    fi
done

# Wait for all background jobs to complete
wait

END=$(date +%s.%N)
TOTAL_TIME=$(echo "$END - $START" | bc)

# Calculate statistics
TOTAL=$(wc -l < "$TMPDIR/results.txt")
SUCCESS=$(grep -c "^200 " "$TMPDIR/results.txt" || echo 0)
FAILED=$((TOTAL - SUCCESS))

echo "📊 Results"
echo "===================="
echo "Total requests: $TOTAL"
echo "Successful: $SUCCESS ($(echo "scale=1; $SUCCESS * 100 / $TOTAL" | bc)%)"
echo "Failed: $FAILED ($(echo "scale=1; $FAILED * 100 / $TOTAL" | bc)%)"
echo "Total time: ${TOTAL_TIME}s"
echo "RPS: $(echo "scale=2; $TOTAL / $TOTAL_TIME" | bc)"
echo ""

# Response time stats
if [ "$SUCCESS" -gt 0 ]; then
    grep "^200 " "$TMPDIR/results.txt" | awk '{print $2}' | sort -n > "$TMPDIR/times.txt"
    
    AVG=$(awk '{sum+=$1} END {print sum/NR}' "$TMPDIR/times.txt")
    MIN=$(head -1 "$TMPDIR/times.txt")
    MAX=$(tail -1 "$TMPDIR/times.txt")
    P95_LINE=$(echo "($SUCCESS * 0.95) / 1" | bc)
    P95=$(sed -n "${P95_LINE}p" "$TMPDIR/times.txt")
    
    echo "⏱️  Response Times"
    echo "===================="
    echo "Average: ${AVG}s"
    echo "Min: ${MIN}s"
    echo "Max: ${MAX}s"
    echo "P95: ${P95}s"
    echo ""
fi

# Recommendations
echo "💡 Recommendations"
echo "===================="
if [ "$FAILED" -eq 0 ] && [ "$(echo "$AVG < 1" | bc)" -eq 1 ]; then
    echo "✅ Excellent performance!"
    echo "   Current settings appear optimal for $WORKERS concurrent workers"
    echo ""
    echo "📊 For production, consider:"
    echo "   - DB_POOL_SIZE=10 (current default)"
    echo "   - DB_MAX_OVERFLOW=20 (current default)"
    echo "   - Total capacity: 30 connections"
    echo ""
    echo "💡 Scale up if you expect >30 concurrent users:"
    echo "   - DB_POOL_SIZE=20"
    echo "   - DB_MAX_OVERFLOW=40"
elif [ "$FAILED" -gt 0 ]; then
    echo "⚠️  Some failures detected"
    echo "   Consider increasing pool size:"
    echo "   - DB_POOL_SIZE=15"
    echo "   - DB_MAX_OVERFLOW=30"
else
    echo "✅ System is handling load well"
    echo "   Current settings are appropriate"
fi

# Cleanup
rm -rf "$TMPDIR"

