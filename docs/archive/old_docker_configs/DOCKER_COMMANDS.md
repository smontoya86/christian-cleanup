# 🐳 Docker Commands Reference

## **DOCKER-FIRST PROJECT**

This project runs entirely in Docker containers. **DO NOT run commands locally** - always use the Docker containers.

## **Quick Status Check**

```bash
# Check all services
docker compose ps

# Check logs
docker compose logs -f web
docker compose logs -f web
```

## **Web Application Commands**

```bash
# Access Flask shell
docker compose exec web flask shell

# Run database migrations
docker compose exec web flask db upgrade

# Check environment variables
docker compose exec web env | grep SPOTIFY

# View application logs
docker compose logs -f web
```

## **Database Commands**

```bash
# Access PostgreSQL shell
docker compose exec db psql -U postgres -d spotify_cleanup

# Database backup
docker compose exec db pg_dump -U postgres -d spotify_cleanup > backup.sql

# Run SQL query
docker compose exec db psql -U postgres -d spotify_cleanup -c "SELECT COUNT(*) FROM songs;"
```

## **Redis Commands**

```bash
# Access Redis CLI
docker compose exec redis redis-cli

# Check queue status
docker compose exec redis redis-cli llen "priority_queue:medium"

# View active workers
docker compose exec redis redis-cli smembers "active_workers"

# Check progress data
docker exec christiancleanupwindsurf-redis-1 redis-cli keys "progress:*"
```

## **Services**

```bash
# Restart web
docker compose restart web
```

## **Service Management**

```bash
# Start all services
docker compose up -d

# Restart specific service
docker compose restart web

# Force recreate with new environment variables
docker compose up -d --force-recreate web

# Scale workers
docker compose up -d --scale worker=8

# Stop all services
docker compose down
```

## **Development Workflow**

```bash
# 1. Check service status
docker compose ps

# 2. View logs for debugging
docker compose logs -f web worker

# 3. Access web application
open http://localhost:5001

# 4. Monitor background analysis
docker compose exec redis redis-cli get "progress:*"

# 5. Check analysis API
curl -s http://localhost:5001/api/background-analysis/public-status | jq
```

## **Troubleshooting**

```bash
# Service not starting?
docker compose logs web

# Database connection issues?
docker compose exec web flask shell -c "from app import db; db.engine.execute('SELECT 1')"

# Worker not processing?
docker compose exec redis redis-cli llen "priority_queue:medium"

# Environment variables missing?
docker compose exec web env | grep -E "(SPOTIFY|DATABASE)"
```

## **AI Assistant Guidelines**

**For AI assistants working on this project:**

1. ✅ **Always use Docker commands** - Never run `python`, `flask`, `pip`, etc. locally
2. ✅ **Use container names** - `christiancleanupwindsurf-web-1`, `christiancleanupwindsurf-worker-1`, etc.
3. ✅ **Check service status first** - `docker-compose ps` before making changes
4. ✅ **Use docker exec** - All application commands should be via `docker exec`
5. ❌ **Never run locally** - No `python run.py`, `flask db upgrade`, etc. on host

**Example: Database Migration**
```bash
# ✅ CORRECT - Via Docker
docker compose exec web flask db upgrade

# ❌ WRONG - Local command
flask db upgrade
```
