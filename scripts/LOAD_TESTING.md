# Load Testing Guide

Comprehensive guide for load testing Christian Cleanup to tune database pool sizes and identify bottlenecks.

## Quick Start

```bash
# Make sure the app is running
docker-compose up -d

# Run a quick test (10 concurrent requests)
python scripts/load_test.py --test quick --workers 10

# Run a comprehensive ramp-up test
python scripts/load_test.py --test rampup

# Run a sustained load test
python scripts/load_test.py --test sustained --duration 60 --rps 20

# Run all tests
python scripts/load_test.py --test all
```

## Test Types

### 1. Quick Test
Fast test with fixed concurrency level.

```bash
python scripts/load_test.py --test quick --workers 20
```

**Use Case**: Quick health check, verify system is responding  
**Duration**: ~5-10 seconds  
**Output**: Success rate, avg response time, cache hit rate

### 2. Ramp-Up Test
Gradually increases concurrency to find breaking point.

```bash
python scripts/load_test.py --test rampup
```

**Default Settings**:
- Start: 5 workers
- Max: 50 workers
- Step: 5 workers
- Requests per level: 20

**Use Case**: Find optimal pool size, identify capacity limits  
**Duration**: ~5-10 minutes  
**Output**: Performance metrics at each concurrency level

### 3. Sustained Load Test
Maintains constant load over time.

```bash
python scripts/load_test.py --test sustained --duration 120 --rps 15
```

**Use Case**: Test stability under continuous load, verify no memory leaks  
**Duration**: Configurable (default: 60 seconds)  
**Output**: Aggregate stats over entire duration

## Interpreting Results

### Success Rate
- **>98%**: Excellent, system handling load well
- **95-98%**: Good, minor issues under load
- **90-95%**: Warning, system struggling
- **<90%**: Critical, system overloaded

### Response Times
- **Avg <1s**: Excellent (cache hits)
- **Avg 1-3s**: Good (API calls with rate limiting)
- **Avg >3s**: Poor (bottleneck or overload)
- **P95 >5s**: Critical, investigate immediately

### Cache Hit Rate
- **>80%**: Excellent, effective caching
- **60-80%**: Good, cache warming up
- **40-60%**: Fair, consider cache TTL adjustments
- **<40%**: Poor, investigate cache strategy

## Tuning Database Pool

### Reading Recommendations

After a ramp-up test, the tool provides recommendations:

```
✅ Optimal concurrency: 30 workers
   - RPS: 45.2
   - Avg response time: 1.234s
   - Failure rate: 2.1%

📊 Recommended DB pool settings:
   - DB_POOL_SIZE=15
   - DB_MAX_OVERFLOW=30
   - Total capacity: 45
```

### Applying Recommendations

Update your `.env` or `docker-compose.yml`:

```bash
DB_POOL_SIZE=15
DB_MAX_OVERFLOW=30
```

Then restart:
```bash
docker-compose restart web
```

### General Guidelines

**For low-traffic sites** (<100 concurrent users):
- `DB_POOL_SIZE=5`
- `DB_MAX_OVERFLOW=10`
- Total: 15 connections

**For medium-traffic sites** (100-500 concurrent users):
- `DB_POOL_SIZE=10`
- `DB_MAX_OVERFLOW=20`
- Total: 30 connections

**For high-traffic sites** (>500 concurrent users):
- `DB_POOL_SIZE=20`
- `DB_MAX_OVERFLOW=40`
- Total: 60 connections

**Note**: PostgreSQL default `max_connections` is 100. Ensure your pool + overflow < max_connections.

## Advanced Options

### Custom URL
```bash
python scripts/load_test.py --url https://your-domain.com --test quick
```

### Specific Song IDs
Edit `load_test.py` and modify the `song_ids` parameter in `test_concurrent_requests()`.

### Custom Ramp-Up Range
Edit `load_test.py` and modify `test_ramp_up()` parameters:
```python
stats_list = tester.test_ramp_up(
    start_workers=10,
    max_workers=100,
    step=10,
    requests_per_level=50
)
```

## Monitoring During Tests

### Admin Dashboard
Monitor real-time metrics while testing:
```
http://localhost:5001/admin/dashboard
```

Watch for:
- Database pool utilization
- Redis cache hit rate
- Rate limiter capacity
- Circuit breaker state

### Logs
```bash
# Follow application logs
docker-compose logs -f web

# Look for warnings
docker-compose logs web | grep -i "warning\|error"
```

### Database
```bash
# Check active connections
docker-compose exec db psql -U postgres -d christian_cleanup -c "SELECT count(*) FROM pg_stat_activity;"

# Check connection details
docker-compose exec db psql -U postgres -d christian_cleanup -c "SELECT pid, usename, application_name, client_addr, state FROM pg_stat_activity;"
```

## Troubleshooting

### High Failure Rates

**Symptoms**: >10% failures during tests  
**Possible Causes**:
- Database pool exhausted
- Rate limiter hitting limits
- Circuit breaker opened

**Solutions**:
1. Check admin dashboard for pool utilization
2. Increase `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`
3. Check logs for rate limiter warnings
4. Verify circuit breaker state

### Slow Response Times

**Symptoms**: Avg response time >5s  
**Possible Causes**:
- Cold cache (first run)
- Actual OpenAI API calls
- Database connection delays

**Solutions**:
1. Warm up cache with initial requests
2. Check cache hit rate (should be >80% after warmup)
3. Monitor Redis health
4. Verify database pool not exhausted

### Connection Errors

**Symptoms**: Connection refused or timeout errors  
**Possible Causes**:
- App not running
- Wrong URL
- Firewall blocking

**Solutions**:
1. Verify app is running: `docker-compose ps`
2. Check URL is correct
3. Test manually: `curl http://localhost:5001/api/health`

## Best Practices

1. **Warm up first**: Run a quick test before ramp-up to populate caches
2. **Test during maintenance windows**: Don't run on production during peak hours
3. **Monitor resources**: Watch CPU, memory, disk I/O during tests
4. **Test incrementally**: Start small, gradually increase load
5. **Document results**: Keep reports for comparison after changes
6. **Retest after changes**: Verify improvements after tuning

## Example Workflow

```bash
# 1. Warm up caches
python scripts/load_test.py --test quick --workers 10

# 2. Find optimal concurrency
python scripts/load_test.py --test rampup

# 3. Apply recommended settings
# Edit .env with recommendations

# 4. Restart and verify
docker-compose restart web

# 5. Validate improvements
python scripts/load_test.py --test rampup

# 6. Test sustained load
python scripts/load_test.py --test sustained --duration 300 --rps 20
```

## Report Files

Reports are saved as:
```
load_test_report_YYYYMMDD_HHMMSS.txt
```

Keep these for:
- Performance baselines
- Before/after comparisons
- Capacity planning
- Incident investigation

