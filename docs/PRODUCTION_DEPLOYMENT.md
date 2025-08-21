# Production Deployment Guide

## Overview

This guide covers the complete production deployment of the Christian Music Curator application using Docker containers with comprehensive monitoring, security, and scalability features.

## Architecture

### Production Stack
- **Web Server**: Nginx (reverse proxy, SSL termination, static files)
- **Application**: Flask + Gunicorn with Gevent workers
- **Database**: PostgreSQL 15 with optimized configuration
- **Cache/Queue**: Redis 7 with persistence
- **Monitoring**: Prometheus + Grafana + Loki stack
- **Security**: Rate limiting, CSRF protection, secure headers

### Network Architecture
```
Internet → Nginx (Port 80/443) → Flask App (Port 5000)
                 ↓
         Static Files (Direct)

App Container → PostgreSQL (Internal)
              → Redis (Internal)
               → (Workers removed in MVP; analysis runs synchronously in app)
```

## Prerequisites

### System Requirements
- **CPU**: Minimum 2 cores, recommended 4+ cores
- **Memory**: Minimum 4GB RAM, recommended 8GB+ RAM
- **Storage**: Minimum 20GB, recommended 50GB+ SSD
- **OS**: Linux (Ubuntu 20.04+ or CentOS 8+)

### Required Software
- Docker 20.10+
- Docker Compose 2.0+
- Git
- OpenSSL (for SSL certificates)
- Curl (for health checks)

### Network Requirements
- Ports 80 (HTTP) and 443 (HTTPS) open to internet
- Port 22 (SSH) for administration
- Outbound HTTPS access for Spotify API

## Pre-Deployment Setup

### 1. Server Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login to apply Docker group membership
```

### 2. Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

# Optional: Allow monitoring ports (restrict to your IP)
sudo ufw allow from YOUR_MONITORING_IP to any port 3000  # Grafana
sudo ufw allow from YOUR_MONITORING_IP to any port 9090  # Prometheus
```

### 3. SSL Certificate Setup

For production, obtain proper SSL certificates:

#### Option A: Let's Encrypt (Recommended)
```bash
# Install Certbot
sudo apt install certbot

# Obtain certificate (replace with your domain)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates to project
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem deploy/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem deploy/ssl/key.pem
sudo chown $USER:$USER deploy/ssl/*.pem
```

#### Option B: Commercial Certificate
```bash
# Copy your commercial certificates
cp your-certificate.crt deploy/ssl/cert.pem
cp your-private-key.key deploy/ssl/key.pem
chmod 600 deploy/ssl/*.pem
```

## Deployment Process

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/your-org/christian-music-curator.git
cd christian-music-curator

# Create production environment file
cp deploy/production.env.example .env.prod

# Edit configuration (see Configuration section below)
nano .env.prod
```

### 2. Configure Environment

Edit `.env.prod` with your production settings:

```bash
# Required settings
SECRET_KEY=your-32-character-or-longer-secret-key
DATABASE_URL=postgresql://christian_user:secure_password@db:5432/christian_cleanup_prod
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
SPOTIFY_REDIRECT_URI=https://yourdomain.com/auth/callback

# PostgreSQL settings
POSTGRES_USER=christian_user
POSTGRES_PASSWORD=secure_database_password
POSTGRES_DB=christian_cleanup_prod

# Monitoring
GRAFANA_ADMIN_PASSWORD=secure_grafana_password
```

### 3. Deploy Application (from source or GHCR)

```bash
# Option A: Build from source
docker-compose -f docker-compose.prod.yml up -d --build

# Option B: Pull prebuilt image from GHCR (after tag release)
export IMAGE=ghcr.io/smontoya86/christian-cleanup:latest
docker pull $IMAGE
IMAGE=$IMAGE docker-compose -f docker-compose.prod.yml up -d
```

### 4. Verify Deployment

```bash
# Check service status
./scripts/deploy.sh status

# Run health checks
./scripts/deploy.sh health

# Check individual services
docker-compose -f docker-compose.prod.yml ps
```

## Configuration

### Environment Variables

#### Required Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session secret | `a-32-character-random-string` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@db:5432/dbname` |
| `SPOTIFY_CLIENT_ID` | Spotify API client ID | `abc123def456` |
| `SPOTIFY_CLIENT_SECRET` | Spotify API secret | `secret123` |
| `SPOTIFY_REDIRECT_URI` | OAuth callback URL | `https://yourdomain.com/auth/callback` |

#### Database Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `DB_POOL_SIZE` | 20 | Connection pool size |
| `DB_MAX_OVERFLOW` | 30 | Max pool overflow |
| `DB_POOL_RECYCLE` | 3600 | Connection recycle time |

#### Performance Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `ANALYSIS_BATCH_SIZE` | 50 | Songs per analysis batch |
| `CACHE_LYRICS_TTL` | 604800 | Lyrics cache TTL (seconds) |
| `USE_LLM_ANALYZER` | 1 | Use local OpenAI-compatible LLM analyzer |
| `LLM_API_BASE_URL` | http://host.docker.internal:8080/v1 | Local MLX/llama.cpp endpoint |
| `LLM_MODEL` | mlx-community/Meta-Llama-3.1-8B-Instruct-4bit | Default local model |

### Resource Limits

The production configuration includes resource limits:

| Service | CPU Limit | Memory Limit |
|---------|-----------|--------------|
| nginx | 0.5 | 256MB |
| web | 1.0 | 1GB |
| worker | 0.5 | 512MB |
| db | 1.0 | 2GB |
| redis | 0.5 | 1GB |

## Monitoring

### Access Dashboards

- **Application**: https://yourdomain.com
- **Grafana**: http://yourdomain.com:3000 (admin/your-password)
- **Prometheus**: http://yourdomain.com:9090

### Key Metrics

#### Application Metrics
- Response time and throughput
- Error rates by endpoint
 - Analysis throughput and error rates
- Analysis completion rates

#### Infrastructure Metrics
- CPU and memory usage
- Disk space and I/O
- Network traffic
- Container health

#### Business Metrics
- User registrations and activity
- Playlist analysis completions
- API usage patterns

### Alerting

Configure alerts in Grafana for:
- High error rates (>5%)
- Slow response times (>2s)
- Queue backlog (>1000 jobs)
- Low disk space (<10%)
- Memory usage (>80%)

## Security

### Production Security Features

1. **Network Security**
   - Internal Docker networks
   - Limited external port exposure
   - Nginx reverse proxy

2. **Application Security**
   - CSRF protection enabled
   - Secure session cookies
   - Rate limiting by IP
   - Security headers (HSTS, CSP, etc.)

3. **Data Security**
   - Encrypted database connections
   - Secure Redis configuration
   - Environment-based secrets

4. **SSL/TLS**
   - HTTPS-only enforcement
   - Modern TLS configuration
   - HSTS headers

### Security Checklist

- [ ] Strong passwords for all services
- [ ] SSL certificates properly configured
- [ ] Firewall rules implemented
- [ ] Security headers verified
- [ ] Rate limiting tested
- [ ] Log monitoring configured
- [ ] Regular security updates scheduled

## Backup and Recovery

### Automated Backups

The system includes automated daily backups:

```bash
# Database backup (daily at 2 AM)
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql

# Volume backup
tar -czf volumes-backup.tar.gz data/
```

### Manual Backup

```bash
# Create manual backup
./scripts/backup.sh

# Backup with custom name
./scripts/backup.sh custom-backup-name
```

### Recovery Process

```bash
# Rollback to previous version
./scripts/deploy.sh rollback

# Restore specific backup
./scripts/restore.sh backup_20231201_120000
```

### Disaster Recovery

1. **Data Loss Prevention**
   - Daily automated backups
   - Off-site backup storage
   - Database replication (optional)

2. **Recovery Time Objectives**
   - RTO: 2 hours maximum downtime
   - RPO: 24 hours maximum data loss

3. **Recovery Procedures**
   - Documented step-by-step process
   - Regular recovery testing
   - Contact information for support

## Scaling

### Horizontal Scaling

Scale individual services:

```bash
# Scale web servers
docker-compose -f docker-compose.prod.yml up -d --scale web=3

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=5
```

### Load Balancing

For multiple web instances, Nginx automatically load balances:

```nginx
upstream christian_cleanup_backend {
    least_conn;
    server web_1:5000;
    server web_2:5000;
    server web_3:5000;
}
```

### Database Scaling

For high-load scenarios:

1. **Read Replicas**: Configure PostgreSQL read replicas
2. **Connection Pooling**: Use PgBouncer for connection management
3. **Query Optimization**: Monitor and optimize slow queries

## Maintenance

### Regular Tasks

#### Daily
- Monitor system health
- Check error logs
- Verify backup completion

#### Weekly
- Review performance metrics
- Update system packages
- Clean up old logs

#### Monthly
- Security vulnerability scan
- Performance optimization review
- Capacity planning assessment

### Updates

#### Application Updates
```bash
# Pull latest code
git pull origin main

# Deploy update
./scripts/deploy.sh

# Verify deployment
./scripts/deploy.sh health
```

#### System Updates
```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### Log Management

#### Log Locations
- Application logs: `/app/logs/`
- Nginx logs: `/var/log/nginx/`
- PostgreSQL logs: `/var/log/postgresql/`

#### Log Rotation
```bash
# Configure logrotate
sudo nano /etc/logrotate.d/christian-cleanup

# Sample configuration
/app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 christian christian
}
```

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service logs
docker-compose -f docker-compose.prod.yml logs service_name

# Check resource usage
docker stats

# Verify configuration
docker-compose -f docker-compose.prod.yml config
```

#### Database Connection Issues
```bash
# Check database status
docker-compose -f docker-compose.prod.yml exec db pg_isready

# Check connection string
echo $DATABASE_URL

# Test connection
docker-compose -f docker-compose.prod.yml exec db psql -U $POSTGRES_USER -d $POSTGRES_DB
```

#### High Memory Usage
```bash
# Check memory usage by service
docker stats --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Restart high-usage services
docker-compose -f docker-compose.prod.yml restart service_name
```

### Performance Issues

#### Slow Response Times
1. Check application metrics in Grafana
2. Review slow query logs
3. Monitor worker queue length
4. Check system resource usage

#### Analysis Performance
1. Verify MLX/llama.cpp server health (`LLM_API_BASE_URL`)
2. Adjust concurrency (`ANALYSIS_MAX_CONCURRENCY` if applicable)
3. Review prompt and chunking settings

### Emergency Procedures

#### Complete System Failure
1. Check Docker daemon status
2. Verify disk space availability
3. Restart all services
4. If needed, restore from backup

#### Security Incident
1. Isolate affected systems
2. Review access logs
3. Update compromised credentials
4. Document incident details

## Support

### Getting Help

1. **Documentation**: Check this guide and inline documentation
2. **Logs**: Review application and system logs
3. **Monitoring**: Use Grafana dashboards for insights
4. **Community**: GitHub issues and discussions

### Contact Information

- **Technical Support**: support@yourdomain.com
- **Security Issues**: security@yourdomain.com
- **Emergency Contact**: +1-XXX-XXX-XXXX

### Useful Commands

```bash
# Quick status check
./scripts/deploy.sh status

# Health check
curl -s https://yourdomain.com/health | jq

# View logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100

# Database shell
docker-compose -f docker-compose.prod.yml exec db psql -U $POSTGRES_USER -d $POSTGRES_DB

# Redis CLI
docker-compose -f docker-compose.prod.yml exec redis redis-cli

# Resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

**Last Updated**: [Current Date]
**Version**: 1.0
**Maintained By**: Development Team
