# Docker Resource Configuration for ML Model Operation

## 📊 **Resource Requirements Analysis**

### **Problem Identified:**
The application loads heavy transformer models which were causing memory exhaustion and OOM kills:
- **BART-large**: ~400-600MB per instance (theme classification)
- **RoBERTa models**: ~250-350MB each (sentiment, emotion, safety)
- **Total per worker**: ~1.2-1.5GB
- **With 4 workers**: ~4.8-6GB + overhead

### **Root Cause:**
```
Multiple Model Loading Pattern:
├── Gunicorn Master Process
├── Worker 1: Loads all 4 models (~1.5GB)
├── Worker 2: Loads all 4 models (~1.5GB)
├── Worker 3: Loads all 4 models (~1.5GB)
└── Worker 4: Loads all 4 models (~1.5GB)
Total: ~6GB + OS overhead = 8GB minimum required
```

## 🔧 **Updated Resource Configuration**

### **Development Environment (docker-compose.yml)**

**Before:**
```yaml
# OLD CONFIGURATION (Insufficient)
command: gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 600 run:app
deploy:
  resources:
    limits:
      memory: 2G      # ❌ TOO LOW
      cpus: '1.0'
    reservations:
      memory: 1G
      cpus: '0.5'
```

**After:**
```yaml
# NEW CONFIGURATION (ML Optimized)
command: gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 1200 --worker-connections 100 --max-requests 50 --max-requests-jitter 10 --preload run:app
deploy:
  resources:
    limits:
      memory: 8G      # ✅ 4x INCREASE for ML models
      cpus: '2.0'     # ✅ 2x INCREASE for ML processing
    reservations:
      memory: 4G      # ✅ 4x INCREASE
      cpus: '1.0'     # ✅ 2x INCREASE
```

### **Production Environment (docker-compose.prod.yml)**

**Before:**
```yaml
# OLD PRODUCTION (Completely insufficient)
command: gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gevent --worker-connections 1000 --timeout 120 run:app
deploy:
  replicas: 2
  resources:
    limits:
      memory: 1G      # ❌ CRITICALLY TOO LOW
      cpus: '1.0'
```

**After:**
```yaml
# NEW PRODUCTION (ML Production Ready)
command: gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 1800 --worker-connections 500 --max-requests 100 --max-requests-jitter 20 --preload run:app
deploy:
  replicas: 1  # Reduced due to memory requirements
  resources:
    limits:
      memory: 12G     # ✅ 12x INCREASE for production ML
      cpus: '4.0'     # ✅ 4x INCREASE for production processing
    reservations:
      memory: 6G      # ✅ 6x INCREASE
      cpus: '2.0'     # ✅ 2x INCREASE
```

## 🚀 **Key Optimizations Applied**

### **1. Worker Configuration**
- **Reduced workers**: 4 → 2 (reduces memory duplication)
- **Increased timeout**: 600s → 1200s (allows for model processing)
- **Reduced max requests**: 1000 → 50 (prevents memory leaks)
- **Added preload**: `--preload` (loads models once per worker)

### **2. Memory Management**
- **Model caching**: Persistent volume for model files
- **Cache environment**: `TRANSFORMERS_CACHE=/root/.cache/huggingface`
- **Memory limits**: Development 8G, Production 12G
- **Reserved memory**: Development 4G, Production 6G

### **3. CPU Optimization**
- **Thread limiting**: `OMP_NUM_THREADS=4/8` (prevents CPU thrashing)
- **MKL optimization**: `MKL_NUM_THREADS=4/8` (Intel math library)
- **CPU allocation**: Development 2 cores, Production 4 cores

### **4. Health Check Adjustments**
- **Increased intervals**: 30s → 60s/90s (accounts for model load time)
- **Longer startup**: 30s → 120s/180s (model initialization time)
- **Higher timeouts**: 10s → 30s/45s (model processing time)

## 📋 **System Requirements**

### **Minimum Host Requirements**

**Development:**
- **RAM**: 16GB total (8GB for Docker, 8GB for host OS)
- **CPU**: 4 cores minimum (2 allocated to Docker)
- **Storage**: 50GB available (model cache + data)

**Production:**
- **RAM**: 24GB total (12GB for Docker, 12GB for host OS + overhead)
- **CPU**: 8 cores minimum (4 allocated to Docker)
- **Storage**: 100GB available (model cache + data + logs)

### **Docker Desktop Settings**

Update Docker Desktop resource allocation:

**Development:**
```bash
# Docker Desktop Settings → Resources → Advanced
Memory: 10GB (leaves 6GB for host)
CPUs: 3 (leaves 1 for host)
Disk: 50GB
```

**Production:**
```bash
# Docker Desktop Settings → Resources → Advanced
Memory: 16GB (leaves 8GB for host)
CPUs: 6 (leaves 2 for host)
Disk: 100GB
```

## 🔄 **Migration Steps**

### **1. Stop Current Services**
```bash
docker-compose down
```

### **2. Update Docker Desktop Resources**
- Open Docker Desktop → Settings → Resources → Advanced
- Increase memory allocation as specified above
- Apply & Restart Docker

### **3. Clean Up Old Containers**
```bash
docker system prune -f
docker volume prune -f
```

### **4. Start with New Configuration**
```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### **5. Verify Resource Usage**
```bash
# Monitor container stats
docker stats

# Check model loading logs
docker logs christiancleanupwindsurf-web-1 | grep "Device set to use"
```

## 📈 **Expected Performance Improvements**

### **Before (with issues):**
- ❌ Worker timeouts every 10 minutes
- ❌ OOM kills: `Worker was sent SIGKILL! Perhaps out of memory?`
- ❌ Models reload on every restart
- ❌ High memory pressure

### **After (optimized):**
- ✅ Stable operation with cached models
- ✅ No OOM kills with proper memory allocation
- ✅ Models persist between container restarts
- ✅ Predictable memory usage pattern

## 🔍 **Monitoring & Troubleshooting**

### **Memory Usage Monitoring**
```bash
# Real-time container stats
docker stats --no-stream

# Detailed memory breakdown
docker exec [container] cat /proc/meminfo
```

### **Model Loading Verification**
```bash
# Check if models are loading once per worker
docker logs [container] | grep -c "Device set to use cpu"
# Should see: 2 (for 2 workers) instead of 8+ (multiple loads)

# Check model cache persistence
docker exec [container] ls -la /root/.cache/huggingface/
```

### **Performance Metrics**
```bash
# Check if analysis completes without timeout
curl -X POST http://localhost:5001/analyze_playlist/1
# Should complete in 30-60 seconds instead of timing out
```

## 🚨 **Troubleshooting Common Issues**

### **Issue: Still getting OOM kills**
**Solution**: Increase host Docker memory allocation

### **Issue: Models still loading multiple times**
**Solution**: Verify `--preload` flag is active in gunicorn command

### **Issue: Slow startup times**
**Solution**: Models cache properly after first load - subsequent startups are faster

### **Issue: High CPU usage**
**Solution**: Adjust `OMP_NUM_THREADS` and `MKL_NUM_THREADS` values

---

**Summary**: Resource allocation has been increased 4-12x to properly support heavy transformer models, with optimized worker configuration and persistent model caching for sustained ML operation.
