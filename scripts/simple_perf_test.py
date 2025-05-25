#!/usr/bin/env python3
import time
import requests
import statistics

print('🚀 CHRISTIAN MUSIC CURATOR - PERFORMANCE TEST')
print('=' * 60)

base_url = 'http://localhost:5000'
endpoints = [
    ('/', 'Home Page'),
    ('/health', 'Health Check'),
    ('/dashboard', 'Dashboard'),
    ('/playlist/3', 'Playlist Detail'),
    ('/api/analysis/progress', 'Progress API'),
    ('/api/analysis/performance', 'Performance API'),
]

print('\n🌐 WEB PAGE & API PERFORMANCE')
print('=' * 50)

for endpoint, name in endpoints:
    url = f'{base_url}{endpoint}'
    times = []
    for i in range(3):
        start = time.time()
        try:
            response = requests.get(url, timeout=10)
            end = time.time()
            if response.status_code == 200:
                times.append((end - start) * 1000)
        except Exception as e:
            print(f'  ❌ {name} failed: {e}')
            break
    
    if times:
        avg = statistics.mean(times)
        if avg < 50:
            status = '🟢 Excellent'
        elif avg < 200:
            status = '🟡 Good'
        elif avg < 1000:
            status = '🟠 Acceptable'
        else:
            status = '🔴 Slow'
        print(f'  {status} {name}: {avg:.1f}ms avg (min: {min(times):.1f}ms, max: {max(times):.1f}ms)')

print('\n✅ Performance testing complete!')
print('\nPerformance Guidelines:')
print('  🟢 Excellent: < 50ms')
print('  🟡 Good: 50-200ms') 
print('  🟠 Acceptable: 200ms-1s')
print('  🔴 Slow: > 1s') 