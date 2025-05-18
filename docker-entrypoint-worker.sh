#!/bin/bash
set -e

# Set the Redis URL
export RQ_REDIS_URL=redis://redis:6379/0

echo "Starting RQ worker with Redis URL: $RQ_REDIS_URL"

# Execute the RQ worker command
exec rq worker --url "$RQ_REDIS_URL" default
