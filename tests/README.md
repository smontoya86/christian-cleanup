# Test Suite

Modern pytest-based test suite for the Christian Cleanup application.

## Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests for individual components
│   ├── test_models.py       # Database models
│   ├── test_router_analyzer.py  # OpenAI analyzer
│   ├── test_analysis_service.py  # Analysis service
│   ├── test_lyrics_fetcher.py    # Lyrics fetching
│   └── test_provider_resolver.py # Provider & cache
├── integration/             # Integration tests
│   ├── test_api_health.py   # API endpoints
│   └── test_analysis_workflow.py # Full workflows
└── fixtures/                # Shared test data
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Suite
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_models.py

# Specific test
pytest tests/unit/test_models.py::TestUserModel::test_create_user
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run in Docker
```bash
docker compose exec web pytest
```

## Test Categories

### Unit Tests
- **Models** - Database model instantiation and relationships
- **RouterAnalyzer** - OpenAI API integration and error handling
- **Analysis Service** - Service layer logic and coordination
- **Lyrics Fetcher** - Caching and API fallback
- **Provider Resolver** - Analyzer selection and caching

### Integration Tests
- **API Health** - Basic endpoint availability
- **Analysis Workflow** - Full analysis pipeline from lyrics to results
- **Batch Processing** - Multiple song analysis

## Fixtures

Key fixtures available in `conftest.py`:

- `app` - Flask application instance
- `client` - Test client for HTTP requests
- `db_session` - Database session with automatic rollback
- `sample_user` - Pre-created user
- `sample_song` - Pre-created song
- `sample_playlist` - Pre-created playlist
- `sample_analysis` - Pre-created analysis result
- `sample_lyrics_cache` - Pre-created lyrics cache
- `mock_openai_response` - Mock OpenAI API response
- `mock_analysis_service` - Mocked analysis service (no real API calls)

## Mocking External Services

### OpenAI API
```python
@patch('requests.post')
def test_analysis(mock_post):
    mock_post.return_value = Mock(json=lambda: {...})
    # Your test code
```

### Use Built-in Mock
```python
def test_with_mock(mock_analysis_service):
    # Analysis service is automatically mocked
    # No real OpenAI API calls will be made
```

## Writing New Tests

### Unit Test Example
```python
def test_new_feature(db_session, sample_user):
    """Test description"""
    # Arrange
    data = {...}
    
    # Act
    result = perform_action(data)
    
    # Assert
    assert result is not None
    assert result.status == 'success'
```

### Integration Test Example
```python
def test_api_endpoint(client, mock_analysis_service):
    """Test API endpoint"""
    response = client.post('/api/analyze', json={
        'title': 'Test Song',
        'artist': 'Test Artist'
    })
    
    assert response.status_code == 200
    assert 'score' in response.json
```

## CI/CD

Tests run automatically in GitHub Actions:
- On every push to main
- On every pull request
- With ruff linting before tests

## Test Data

- Uses in-memory SQLite database for speed
- Automatic transaction rollback after each test
- No persistent data between tests
- Mock data available via fixtures

## Best Practices

1. **Isolate tests** - Each test should be independent
2. **Use fixtures** - Reuse common setup via fixtures
3. **Mock external APIs** - Don't make real API calls in tests
4. **Descriptive names** - Test names should explain what they test
5. **AAA pattern** - Arrange, Act, Assert
6. **Clean up** - Use fixtures with automatic cleanup
7. **Fast tests** - Unit tests should run in milliseconds

## Debugging

### Run with verbose output
```bash
pytest -v
```

### Run with print statements
```bash
pytest -s
```

### Debug a failing test
```bash
pytest tests/unit/test_models.py::TestUserModel::test_create_user -vv --pdb
```

### See test coverage
```bash
pytest --cov=app --cov-report=term-missing
```

## Maintenance

- Keep tests up to date with code changes
- Add tests for new features
- Update fixtures when models change
- Remove tests for deprecated features
- Monitor test execution time
- Keep test coverage above 70%

## Support

For questions or issues with the test suite, see:
- `pytest.ini` - pytest configuration
- `conftest.py` - fixture definitions
- `.github/workflows/` - CI configuration

