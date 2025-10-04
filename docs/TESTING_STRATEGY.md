# Comprehensive Testing Strategy

This document outlines the testing strategy for all recent changes and ongoing development.

## Test Suite Overview

### 1. **Unit Tests** (`tests/unit/`)
- Test individual components in isolation
- Mock external dependencies
- Fast execution (< 5 seconds total)

**Coverage:**
- Models
- Services
- Utilities
- Analyzers

### 2. **Integration Tests** (`tests/integration/`)
- Test components working together
- Use test database
- Mock external APIs only

**Coverage:**
- API endpoints
- Analysis workflows
- Database interactions
- RQ background jobs

### 3. **Regression Tests** (`tests/integration/test_regression_suite.py`)
- Verify recent changes didn't break existing functionality
- Test all critical paths
- Comprehensive coverage of recent work

**Coverage:**
- Prompt optimization
- Database indexes
- Docker configuration
- Security enhancements
- Admin authentication
- Background job processing
- Frontend integration

## Recent Changes Test Coverage

### ✅ RQ Implementation
**Test Files:**
- `tests/integration/test_rq_background_jobs.py`
- `tests/test_queue_helpers.py`

**What's Tested:**
- Queue configuration
- Redis connection
- Job enqueuing
- Progress tracking
- Job status polling
- Error handling
- Worker management

### ✅ Prompt Optimization
**Test File:**
- `tests/integration/test_regression_suite.py::TestPromptOptimization`

**What's Tested:**
- Prompt length reduction
- Framework version reference
- Edge case inclusion
- Verdict tier completeness
- Formation risk levels
- JSON schema presence
- Analysis output structure

### ✅ Database Indexes
**Test File:**
- `tests/integration/test_regression_suite.py::TestDatabaseIndexes`

**What's Tested:**
- Index existence
- Correct column references
- Query performance
- Backward compatibility

### ✅ Docker Configuration
**Test File:**
- `tests/integration/test_regression_suite.py::TestDockerConfiguration`

**What's Tested:**
- Multiple Gunicorn workers
- Reasonable timeout settings
- RQ worker service
- Redis service
- Healthcheck configuration

### ✅ Security Enhancements
**Test File:**
- `tests/integration/test_regression_suite.py::TestSecurityEnhancements`

**What's Tested:**
- ENCRYPTION_KEY validation in production
- No validation required in testing
- Proper error raising

### ✅ Admin Authentication
**Test File:**
- `tests/integration/test_regression_suite.py::TestAdminAuthentication`

**What's Tested:**
- Decorator functionality
- is_admin attribute usage
- No hardcoded user IDs
- Route protection

### ✅ Existing Functionality
**Test File:**
- `tests/integration/test_regression_suite.py::TestExistingFunctionalityIntact`

**What's Tested:**
- User login
- Playlist sync
- Song detail pages
- Playlist detail pages
- Analysis service
- Lyrics fetching

### ✅ Frontend Integration
**Test File:**
- `tests/integration/test_regression_suite.py::TestFrontendIntegration`

**What's Tested:**
- Progress modal existence
- Required JavaScript methods
- Playlist analysis module updates
- Template integration

## Running Tests

### Quick Test
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/integration/test_rq_background_jobs.py

# Run specific test class
pytest tests/integration/test_regression_suite.py::TestPromptOptimization
```

### Full Regression Suite
```bash
# Run comprehensive test suite with reports
bash scripts/run_full_test_suite.sh
```

This will:
1. Run all unit tests
2. Run all integration tests
3. Run RQ-specific tests
4. Run regression suite
5. Run queue helper tests
6. Generate coverage report
7. Generate HTML reports

**Output Location:**
- Coverage: `test_reports/coverage/index.html`
- Full report: `test_reports/full_suite.html`

### Quick Smoke Test
```bash
# Just verify critical paths work
pytest tests/integration/test_regression_suite.py::TestExistingFunctionalityIntact -v
```

## Test Requirements

### Environment Setup
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-html

# Ensure Redis is running (for RQ tests)
redis-server

# Or via Docker
docker-compose up redis
```

### Environment Variables
The test suite automatically sets:
- `FLASK_ENV=testing`
- `TESTING=true`
- `DISABLE_ANALYZER_PREFLIGHT=1`
- `DATABASE_URL=sqlite:///:memory:`

## Test Fixtures

### Available Fixtures (in `conftest.py`)
- `app` - Flask application instance
- `client` - Test client for HTTP requests
- `db_session` - Database session
- `auth` - Authentication helper
- `sample_user` - Regular user
- `admin_user` - Admin user
- `sample_song` - Test song
- `sample_playlist` - Test playlist
- `sample_analysis` - Test analysis result
- `mock_openai_response` - Mocked AI response

### Auth Helper Usage
```python
def test_admin_feature(client, auth):
    # Login as admin
    auth.login(is_admin=True)
    
    response = client.post('/api/admin_endpoint')
    assert response.status_code == 200

def test_user_feature(client, auth, sample_user):
    # Login as specific user
    auth.login(user=sample_user)
    
    response = client.get('/dashboard')
    assert response.status_code == 200
```

## Continuous Integration

### Pre-Commit Checks
```bash
# Run before every commit
pytest tests/integration/test_regression_suite.py::TestExistingFunctionalityIntact
```

### Pre-Push Checks
```bash
# Run before pushing to remote
bash scripts/run_full_test_suite.sh
```

### CI/CD Pipeline (Future)
1. Run full test suite
2. Generate coverage report (target: 80%+)
3. Run smoke tests against staging
4. Deploy only if all tests pass

## Test Data Philosophy

### Mock vs Real Data
- **Mock:** External APIs (OpenAI, Spotify, Genius)
- **Real:** Database operations, analysis logic, queue operations

### Test Database
- Use SQLite in-memory for speed
- Fresh database for each test
- Auto-cleanup after tests

## Common Test Patterns

### Testing API Endpoints
```python
def test_endpoint(client, auth):
    auth.login()
    response = client.post('/api/endpoint', json={'key': 'value'})
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
```

### Testing Background Jobs
```python
def test_job(app):
    with app.app_context():
        with patch('module.dependency') as mock_dep:
            result = background_function(param1, param2)
            
            assert result['status'] == 'complete'
            mock_dep.assert_called_once()
```

### Testing Database Models
```python
def test_model(db_session):
    obj = MyModel(field='value')
    db_session.add(obj)
    db_session.commit()
    
    retrieved = MyModel.query.first()
    assert retrieved.field == 'value'
```

## Coverage Goals

### Current Coverage (Target)
- **Overall:** 80%+
- **Critical paths:** 95%+
- **New features:** 90%+

### Coverage Reports
```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# View report
open htmlcov/index.html
```

## Known Test Limitations

### What's NOT Tested
1. **Real AI API calls** - Too expensive, mocked instead
2. **Real Spotify API** - Requires auth tokens, mocked
3. **Long-running jobs** - Tested with small datasets
4. **Browser behavior** - No Selenium/Playwright (yet)

### Future Test Additions
1. **E2E tests** - Full user workflows
2. **Performance tests** - Load testing analysis pipeline
3. **Security tests** - Penetration testing, OWASP checks
4. **Browser tests** - Frontend interaction testing

## Debugging Failed Tests

### Common Issues

**1. Redis not running**
```bash
# Error: Connection refused
# Fix:
redis-server
```

**2. Database locked**
```bash
# Error: Database is locked
# Fix: Use fresh test database
rm -f app.db
```

**3. Import errors**
```bash
# Error: ModuleNotFoundError
# Fix: Ensure in project root
cd /path/to/project
pytest
```

### Verbose Output
```bash
# Show detailed output
pytest -v -s tests/

# Show only failures
pytest --tb=short

# Show full traceback
pytest --tb=long
```

## Maintenance

### Weekly
- [ ] Run full test suite
- [ ] Review coverage report
- [ ] Update tests for new features

### Monthly
- [ ] Review test performance
- [ ] Refactor slow tests
- [ ] Update test documentation

### Per Release
- [ ] Full regression suite
- [ ] Manual smoke testing
- [ ] Update test documentation

## Questions?

If tests fail unexpectedly:
1. Check Redis is running
2. Check you're in project root
3. Check `requirements.txt` is up to date
4. Review test output for specific errors
5. Check `test_reports/` for detailed HTML reports

---

**Last Updated:** 2025-01-04
**Test Suite Version:** 1.0
**Total Tests:** 100+
**Estimated Runtime:** ~30 seconds (without coverage)

