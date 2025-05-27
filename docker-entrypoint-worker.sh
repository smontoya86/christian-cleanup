#!/bin/bash
set -e

# Set the Redis URL for Docker
export RQ_REDIS_URL=redis://redis:6379/0

# Force comprehensive analysis
export USE_LIGHTWEIGHT_ANALYZER=false

echo "Starting RQ worker with Redis URL: $RQ_REDIS_URL"
echo "Comprehensive analysis mode: enabled"

# Execute the RQ worker command to handle all priority queues
exec rq worker --url "$RQ_REDIS_URL" high default low
