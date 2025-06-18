# Utility Scripts

This directory contains production-ready utility scripts for system administration and debugging.

## Available Utilities

### `queue_status_checker.py`
**Purpose**: Monitor RQ queue status and job health  
**Usage**:
```bash
# Basic queue status check
python scripts/utils/queue_status_checker.py

# Verbose mode with job details
python scripts/utils/queue_status_checker.py --verbose

# Check worker health
python scripts/utils/queue_status_checker.py --workers

# Custom Redis URL
python scripts/utils/queue_status_checker.py --redis-url redis://localhost:6379/1

# Check specific queues
python scripts/utils/queue_status_checker.py --queues high default
```

**Features**:
- Real-time queue status monitoring
- Job details and statistics
- Worker health checks
- Error handling with connection validation
- Command-line argument support

### `system_verification.py`
**Purpose**: Comprehensive system health checks  
**Usage**:
```bash
# Run full system verification
python scripts/utils/system_verification.py
```

**Test Coverage**:
- Database connectivity and statistics
- Analysis service functionality
- Error handling system verification
- Redis connectivity and queue system
- Spotify service integration
- Application route health checks

**Use Cases**:
- Pre-deployment verification
- System health monitoring
- Troubleshooting system issues
- Production readiness checks

## Directory Structure

```
scripts/utils/
├── README.md                 # This documentation
├── queue_status_checker.py   # Queue monitoring utility
└── system_verification.py    # System health verification
```

## Integration Notes

- Both scripts are designed to work with the application's existing configuration
- Scripts automatically detect the application directory structure
- Error handling follows the application's patterns
- Output is formatted for both human reading and log parsing

## Development Notes

These utilities were consolidated from various debug scripts during the cleanup process:
- `queue_status_checker.py` - Based on `scripts/debug/check_queue_status.py`
- `system_verification.py` - Based on `scripts/debug/test_analysis_flow.py`

The consolidated versions include:
- Enhanced error handling
- Better command-line interfaces
- Production-ready logging
- Comprehensive documentation
- Standardized output formatting

## Maintenance

When updating these utilities:
1. Maintain backward compatibility for command-line arguments
2. Keep error messages clear and actionable
3. Update this README with any new features
4. Test with both development and production configurations 