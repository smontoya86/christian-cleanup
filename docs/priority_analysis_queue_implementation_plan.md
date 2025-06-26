# Priority-Based Analysis Queue Implementation Plan

## 🎯 **Project Overview**

Implement a priority-based analysis queue system that ensures user-initiated actions take precedence over background analysis, with context-aware progress tracking and automatic analysis on login.

### **Core Principles**
- ✅ **Single Analysis at a Time**: No concurrency, priority-based interruption only
- ✅ **Context-Aware Progress**: Show relevant progress based on current page
- ✅ **Simple Queue**: Redis-based with basic priority levels
- ✅ **Docker-First**: Designed for container deployment
- ✅ **Resume on Restart**: Persist progress and resume analysis after container restarts

---

## 📋 **Phase 1: Core Priority Queue Infrastructure**

### **1.1 Priority Queue Service**
**Estimated Time**: 4-6 hours

**Subtasks**:
- [ ] Create `app/services/priority_analysis_queue.py`
  - [ ] Implement `PriorityAnalysisQueue` class with Redis sorted sets
  - [ ] Add methods: `enqueue()`, `dequeue()`, `get_queue_status()`, `clear_queue()`
  - [ ] Define priority levels: `high` (user song), `medium` (user playlist), `low` (background)
  - [ ] Add job persistence with Redis hashes
  - [ ] Implement queue inspection methods for debugging

- [ ] Create job data structures
  - [ ] Define `AnalysisJob` dataclass with fields: `job_id`, `type`, `priority`, `user_id`, `target_id`, `created_at`
  - [ ] Add job types: `SONG_ANALYSIS`, `PLAYLIST_ANALYSIS`, `BACKGROUND_ANALYSIS`
  - [ ] Include metadata fields for progress tracking

**Acceptance Criteria**:
- [ ] Can enqueue jobs with different priorities
- [ ] Higher priority jobs are dequeued first
- [ ] Job data persists in Redis
- [ ] Queue status can be inspected

### **1.2 Analysis Worker Refactoring**
**Estimated Time**: 6-8 hours

**Subtasks**:
- [ ] Modify `worker.py` to use priority queue
  - [ ] Replace current job pulling with `PriorityAnalysisQueue.dequeue()`
  - [ ] Add graceful interruption logic for higher priority jobs
  - [ ] Implement job status tracking: `pending`, `in_progress`, `completed`, `interrupted`
  - [ ] Add worker heartbeat mechanism

- [ ] Update `UnifiedAnalysisService`
  - [ ] Modify to work with priority queue jobs
  - [ ] Add progress callback support
  - [ ] Implement interruption detection and cleanup
  - [ ] Add resume capability for interrupted jobs

- [ ] Create worker management commands
  - [ ] Add `start_priority_worker.py` script
  - [ ] Implement graceful shutdown handling
  - [ ] Add worker status monitoring

**Acceptance Criteria**:
- [ ] Worker processes jobs by priority
- [ ] Higher priority jobs can interrupt lower priority ones
- [ ] Worker gracefully handles shutdown
- [ ] Job status is accurately tracked

### **1.3 Integration with Existing Routes**
**Estimated Time**: 3-4 hours

**Subtasks**:
- [ ] Update playlist analysis route (`/api/playlists/<id>/analyze`)
  - [ ] Replace direct analysis call with priority queue enqueue
  - [ ] Set priority to `medium`
  - [ ] Return job ID for progress tracking

- [ ] Update song analysis route (`/api/songs/<id>/analyze`)
  - [ ] Replace direct analysis call with priority queue enqueue
  - [ ] Set priority to `high`
  - [ ] Return job ID for progress tracking

- [ ] Maintain backward compatibility
  - [ ] Ensure existing frontend code continues to work
  - [ ] Add migration path for in-progress analyses

**Acceptance Criteria**:
- [ ] Existing analysis buttons work with new queue system
- [ ] Job IDs are returned to frontend
- [ ] No breaking changes to API responses

---

## 📊 **Phase 2: Progress Tracking & ETA**

### **2.1 Progress Tracking Service**
**Estimated Time**: 4-5 hours

**Subtasks**:
- [ ] Create `app/services/progress_tracker.py`
  - [ ] Implement `ProgressTracker` class with Redis storage
  - [ ] Add methods: `update_progress()`, `get_progress()`, `clear_progress()`
  - [ ] Store progress with TTL (24 hours)
  - [ ] Include fields: `current`, `total`, `percentage`, `eta_seconds`, `status`

- [ ] Add ETA calculation
  - [ ] Implement simple time-based ETA: `(total - current) * avg_time_per_item`
  - [ ] Track analysis start time and current progress
  - [ ] Handle edge cases (zero progress, completion)
  - [ ] Format ETA as human-readable strings

- [ ] Integrate with analysis services
  - [ ] Add progress callbacks to `UnifiedAnalysisService`
  - [ ] Update progress during song analysis loops
  - [ ] Handle progress for different analysis types

**Acceptance Criteria**:
- [ ] Progress is tracked and persisted in Redis
- [ ] ETA calculations are reasonably accurate
- [ ] Progress survives worker restarts
- [ ] Multiple concurrent progress tracking works

### **2.2 Context-Aware Progress API**
**Estimated Time**: 3-4 hours

**Subtasks**:
- [ ] Create progress API endpoints
  - [ ] Add `/api/progress/<job_id>` for specific job progress
  - [ ] Add `/api/progress/global` for overall analysis progress
  - [ ] Add `/api/progress/playlist/<id>` for playlist-specific progress
  - [ ] Return appropriate progress based on context

- [ ] Implement progress aggregation
  - [ ] Calculate global progress across all user's unanalyzed songs
  - [ ] Determine playlist-specific progress
  - [ ] Handle multiple concurrent analyses

- [ ] Add real-time updates
  - [ ] Consider WebSocket support for live updates (optional)
  - [ ] Optimize polling frequency recommendations
  - [ ] Add progress change detection

**Acceptance Criteria**:
- [ ] API returns context-appropriate progress
- [ ] Global progress shows overall analysis state
- [ ] Playlist progress shows playlist-specific state
- [ ] Progress updates are efficient and real-time

### **2.3 Frontend Progress Integration**
**Estimated Time**: 4-6 hours

**Subtasks**:
- [ ] Update dashboard progress display
  - [ ] Show global analysis progress with ETA
  - [ ] Display current analysis type and target
  - [ ] Add pause/resume functionality (if applicable)

- [ ] Update playlist detail progress
  - [ ] Show playlist-specific progress when analyzing
  - [ ] Switch to playlist progress when user clicks "Analyze Playlist"
  - [ ] Maintain global progress display when not playlist-focused

- [ ] Enhance progress indicators
  - [ ] Add ETA display to existing progress bars
  - [ ] Show analysis type (background/playlist/song)
  - [ ] Add visual priority indicators
  - [ ] Improve progress bar animations

**Acceptance Criteria**:
- [ ] Dashboard shows global progress with ETA
- [ ] Playlist pages show context-aware progress
- [ ] Progress indicators are visually appealing
- [ ] ETA updates are smooth and accurate

---

## 🚀 **Phase 3: Auto-Analysis & Background Processing**

### **3.1 Login-Triggered Analysis**
**Estimated Time**: 3-4 hours

**Subtasks**:
- [ ] Create background analysis service
  - [ ] Add `app/services/background_analysis_service.py`
  - [ ] Implement `trigger_background_analysis()` method
  - [ ] Find all unanalyzed songs for user
  - [ ] Enqueue background analysis jobs with `low` priority

- [ ] Integrate with authentication
  - [ ] Add background analysis trigger to login route
  - [ ] Check if analysis is already running before triggering
  - [ ] Add user preference to enable/disable auto-analysis
  - [ ] Track last analysis timestamp

- [ ] Add analysis resumption
  - [ ] Detect interrupted background analyses on startup
  - [ ] Resume from last completed song
  - [ ] Handle partial playlist analyses

**Acceptance Criteria**:
- [ ] Background analysis starts automatically on login
- [ ] Only triggers if not already running
- [ ] Resumes interrupted analyses correctly
- [ ] Respects user preferences

### **3.2 Smart Analysis Batching**
**Estimated Time**: 4-5 hours

**Subtasks**:
- [ ] Implement intelligent batching
  - [ ] Group songs by playlist for efficient processing
  - [ ] Prioritize recently added songs
  - [ ] Batch similar analysis types together
  - [ ] Add batch size configuration

- [ ] Add analysis optimization
  - [ ] Skip already analyzed songs
  - [ ] Detect and handle duplicate songs
  - [ ] Implement smart retry logic for failed analyses
  - [ ] Add analysis result caching

- [ ] Create analysis scheduling
  - [ ] Add time-based analysis scheduling (off-peak hours)
  - [ ] Implement analysis rate limiting
  - [ ] Add resource usage monitoring
  - [ ] Handle multiple users efficiently

**Acceptance Criteria**:
- [ ] Background analysis is efficient and optimized
- [ ] Batching reduces redundant work
- [ ] System handles multiple users well
- [ ] Resource usage is controlled

### **3.3 Notification & User Awareness**
**Estimated Time**: 3-4 hours

**Subtasks**:
- [ ] Add analysis notifications
  - [ ] Show toast notifications when analysis starts/completes
  - [ ] Display analysis summary after completion
  - [ ] Add analysis history tracking
  - [ ] Implement notification preferences

- [ ] Create analysis dashboard
  - [ ] Add analysis statistics (total analyzed, time taken, etc.)
  - [ ] Show analysis history and logs
  - [ ] Display queue status and worker health
  - [ ] Add manual analysis controls

- [ ] Enhance user experience
  - [ ] Add analysis pause/resume controls
  - [ ] Show estimated completion times
  - [ ] Display analysis benefits/results
  - [ ] Add analysis scheduling preferences

**Acceptance Criteria**:
- [ ] Users are informed about analysis progress
- [ ] Analysis completion is celebrated
- [ ] Users can control analysis behavior
- [ ] Analysis value is clearly communicated

---

## 🛠 **Phase 4: Production Readiness**

### **4.1 Redis Configuration & Persistence**
**Estimated Time**: 2-3 hours

**Subtasks**:
- [ ] Configure Redis for production
  - [ ] Update `docker-compose.yml` with AOF persistence
  - [ ] Set appropriate memory limits and eviction policies
  - [ ] Configure Redis password and security
  - [ ] Add Redis health checks

- [ ] Implement data cleanup
  - [ ] Add TTL for completed jobs and progress data
  - [ ] Implement periodic cleanup of old analysis results
  - [ ] Add Redis memory monitoring
  - [ ] Configure automatic data expiration

**Acceptance Criteria**:
- [ ] Redis data persists across container restarts
- [ ] Memory usage is controlled and monitored
- [ ] Security is properly configured
- [ ] Old data is automatically cleaned up

### **4.2 Monitoring & Observability**
**Estimated Time**: 4-5 hours

**Subtasks**:
- [ ] Add queue monitoring
  - [ ] Create admin dashboard for queue status
  - [ ] Add metrics for queue length, processing time, success rate
  - [ ] Implement alerts for queue backup or worker failures
  - [ ] Add worker health monitoring

- [ ] Enhance logging
  - [ ] Add structured logging for analysis jobs
  - [ ] Log queue operations and priority changes
  - [ ] Add performance metrics logging
  - [ ] Implement log aggregation

- [ ] Create debugging tools
  - [ ] Add queue inspection commands
  - [ ] Implement job replay functionality
  - [ ] Add analysis debugging endpoints
  - [ ] Create worker diagnostic tools

**Acceptance Criteria**:
- [ ] Queue health is visible and monitored
- [ ] Issues can be quickly diagnosed
- [ ] Performance metrics are tracked
- [ ] Debugging tools are available

### **4.3 Error Handling & Recovery**
**Estimated Time**: 3-4 hours

**Subtasks**:
- [ ] Implement robust error handling
  - [ ] Add retry logic for failed analyses
  - [ ] Handle Redis connection failures gracefully
  - [ ] Implement circuit breaker patterns
  - [ ] Add fallback mechanisms

- [ ] Create recovery procedures
  - [ ] Add manual job recovery commands
  - [ ] Implement queue repair tools
  - [ ] Add data consistency checks
  - [ ] Create backup and restore procedures

- [ ] Add failure notifications
  - [ ] Alert on repeated analysis failures
  - [ ] Notify on worker crashes or queue issues
  - [ ] Add failure rate monitoring
  - [ ] Implement escalation procedures

**Acceptance Criteria**:
- [ ] System recovers gracefully from failures
- [ ] Failed jobs can be retried or recovered
- [ ] Administrators are notified of issues
- [ ] Data consistency is maintained

---

## 🧪 **Phase 5: Testing & Validation**

### **5.1 Unit Testing**
**Estimated Time**: 6-8 hours

**Subtasks**:
- [ ] Test priority queue functionality
  - [ ] Test job enqueue/dequeue with different priorities
  - [ ] Test queue interruption and resumption
  - [ ] Test job persistence and recovery
  - [ ] Test concurrent queue operations

- [ ] Test progress tracking
  - [ ] Test progress updates and ETA calculations
  - [ ] Test progress persistence across restarts
  - [ ] Test context-aware progress retrieval
  - [ ] Test progress cleanup and TTL

- [ ] Test analysis services
  - [ ] Test background analysis triggering
  - [ ] Test analysis interruption and resumption
  - [ ] Test error handling and retries
  - [ ] Test integration with existing analysis code

**Acceptance Criteria**:
- [ ] All core functionality is unit tested
- [ ] Tests cover edge cases and error conditions
- [ ] Test coverage is >90%
- [ ] Tests run reliably in CI/CD

### **5.2 Integration Testing**
**Estimated Time**: 4-6 hours

**Subtasks**:
- [ ] Test end-to-end workflows
  - [ ] Test login → background analysis → completion flow
  - [ ] Test user playlist analysis interrupting background
  - [ ] Test user song analysis interrupting playlist
  - [ ] Test multiple user scenarios

- [ ] Test system resilience
  - [ ] Test Redis restart scenarios
  - [ ] Test worker restart scenarios
  - [ ] Test network interruption handling
  - [ ] Test high load scenarios

- [ ] Test API integration
  - [ ] Test all new API endpoints
  - [ ] Test frontend integration
  - [ ] Test progress polling behavior
  - [ ] Test error response handling

**Acceptance Criteria**:
- [ ] End-to-end workflows work correctly
- [ ] System handles failures gracefully
- [ ] API integration is solid
- [ ] Performance is acceptable under load

### **5.3 User Acceptance Testing**
**Estimated Time**: 2-3 hours

**Subtasks**:
- [ ] Test user experience flows
  - [ ] Test login and automatic analysis start
  - [ ] Test playlist analysis with progress
  - [ ] Test song analysis priority
  - [ ] Test progress display and ETA accuracy

- [ ] Validate performance improvements
  - [ ] Measure analysis completion times
  - [ ] Verify priority-based execution
  - [ ] Test system responsiveness
  - [ ] Validate progress accuracy

**Acceptance Criteria**:
- [ ] User experience is smooth and intuitive
- [ ] Priority system works as expected
- [ ] Progress tracking is accurate
- [ ] Performance meets requirements

---

## 📚 **Documentation & Deployment**

### **6.1 Documentation**
**Estimated Time**: 3-4 hours

**Subtasks**:
- [ ] Update API documentation
  - [ ] Document new progress endpoints
  - [ ] Document queue management endpoints
  - [ ] Update analysis endpoint documentation
  - [ ] Add troubleshooting guides

- [ ] Create operational guides
  - [ ] Document queue monitoring procedures
  - [ ] Create worker management guide
  - [ ] Document Redis configuration
  - [ ] Add debugging procedures

- [ ] Update deployment documentation
  - [ ] Update Docker configuration docs
  - [ ] Document environment variables
  - [ ] Add scaling recommendations
  - [ ] Update production deployment guide

**Acceptance Criteria**:
- [ ] All new features are documented
- [ ] Operational procedures are clear
- [ ] Deployment is well-documented
- [ ] Troubleshooting guides are comprehensive

### **6.2 Deployment & Migration**
**Estimated Time**: 2-3 hours

**Subtasks**:
- [ ] Create migration scripts
  - [ ] Migrate existing analysis jobs to new queue
  - [ ] Update Redis configuration
  - [ ] Add new environment variables
  - [ ] Test migration procedures

- [ ] Deploy to production
  - [ ] Update Docker containers
  - [ ] Configure Redis persistence
  - [ ] Start new worker processes
  - [ ] Monitor deployment success

**Acceptance Criteria**:
- [ ] Migration completes without data loss
- [ ] Production deployment is successful
- [ ] All systems are operational
- [ ] Monitoring confirms correct operation

---

## 📊 **Success Metrics**

### **Performance Metrics**
- [ ] **Analysis Throughput**: Measure songs analyzed per hour
- [ ] **Priority Compliance**: Verify high-priority jobs execute first
- [ ] **Progress Accuracy**: ETA accuracy within 20%
- [ ] **System Responsiveness**: User actions complete within 2 seconds

### **User Experience Metrics**
- [ ] **Auto-Analysis Adoption**: % of users with auto-analysis enabled
- [ ] **Progress Engagement**: Time users spend watching progress
- [ ] **Analysis Completion**: % of analyses that complete successfully
- [ ] **User Satisfaction**: Feedback on analysis experience

### **System Health Metrics**
- [ ] **Queue Health**: Average queue length and processing time
- [ ] **Worker Uptime**: Worker availability and restart frequency
- [ ] **Error Rate**: Analysis failure rate and recovery time
- [ ] **Resource Usage**: CPU, memory, and Redis usage patterns

---

## ⚠️ **Risk Mitigation**

### **Technical Risks**
- [ ] **Redis Memory Usage**: Monitor and implement cleanup procedures
- [ ] **Worker Crashes**: Implement health checks and auto-restart
- [ ] **Queue Backup**: Add monitoring and alerting for queue length
- [ ] **Data Loss**: Ensure proper Redis persistence configuration

### **User Experience Risks**
- [ ] **Progress Accuracy**: Test ETA calculations thoroughly
- [ ] **System Responsiveness**: Load test priority interruption
- [ ] **Analysis Failures**: Implement robust error handling
- [ ] **Migration Issues**: Test migration procedures extensively

---

## 🎯 **Total Estimated Timeline**

**Development**: 45-65 hours (6-8 weeks part-time)
**Testing**: 12-17 hours (1.5-2 weeks part-time)
**Documentation**: 5-7 hours (1 week part-time)

**Total**: 62-89 hours (8.5-12 weeks part-time)

---

## 🚀 **Getting Started**

1. **Review and approve this plan**
2. **Set up development branch**: `git checkout -b feature/priority-analysis-queue`
3. **Start with Phase 1.1**: Create the core priority queue service
4. **Iterate and test**: Complete each subtask with testing
5. **Regular check-ins**: Review progress and adjust timeline as needed

---

*This plan prioritizes simplicity, reliability, and user experience while maintaining the existing functionality. Each phase builds upon the previous one, allowing for incremental development and testing.* 