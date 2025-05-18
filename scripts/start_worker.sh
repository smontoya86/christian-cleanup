#!/bin/bash
# Start RQ worker for processing background jobs

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root directory
cd "$PROJECT_ROOT" || exit 1

echo "Starting RQ worker..."
echo "Project root: $PROJECT_ROOT"
echo "Environment: ${FLASK_ENV:-development}"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating .venv virtual environment..."
    source .venv/bin/activate
fi

# Set environment variables if .env exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file"
    # Use a while loop to handle potential spaces in variable values
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        if [[ $line =~ ^[^#].* ]] && [[ -n "${line// }" ]]; then
            # Export the variable properly
            export "${line?}" 2>/dev/null || true
        fi
    done < .env
fi

# Ensure required environment variables are set
export FLASK_APP=app

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the RQ worker with proper Python path
echo "Starting RQ worker with queues: default"
PYTHONPATH="$PROJECT_ROOT" rq worker \
    --with-scheduler \
    --path "$PROJECT_ROOT" \
    --name "christian_cleanup_worker" \
    --results-ttl 86400 \
    --worker-ttl 3600 \
    --log-format "%(asctime)s - %(name)s - %(levelname)s - %(message)s" \
    --log-file "$PROJECT_ROOT/logs/worker.log" \
    -c app.worker_config \
    default

echo "RQ worker started. Use Ctrl+C to stop."
