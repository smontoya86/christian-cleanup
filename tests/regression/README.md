# Regression Tests

This directory contains regression tests for the Christian Music Curator application. These tests ensure that previously working functionality continues to work after code changes.

## Current Test Files

### `test_redis_connectivity.py`
- **Purpose**: Tests Redis caching and cache management functionality
- **Focus**: Graceful degradation when cache operations fail
- **Key Scenarios**: Cache stats failures, cache cleanup operations

### `test_rate_limiting.py`
- **Purpose**: Tests API rate limiting and provider fallback behavior
- **Focus**: Graceful handling of rate limits from external APIs
- **Key Scenarios**: Spotify and Genius API rate limits, concurrent request handling, provider fallback

### `test_sqlalchemy_issues.py`
- **Purpose**: Tests database session management and SQLAlchemy functionality
- **Focus**: Proper session lifecycle, model relationships, transaction safety
- **Key Scenarios**: Session management, relationship integrity, concurrent access, rollback behavior

## Test Philosophy

These regression tests are designed to:

1. **Test Real Scenarios**: Focus on issues that have actually occurred in production
2. **Graceful Degradation**: Ensure the system handles failures without crashing
3. **Simplified Architecture**: Test the current simplified system, not legacy complexity
4. **Essential Functionality**: Cover core application behavior that must continue working

## Running Regression Tests

```bash
# Run all regression tests
python -m pytest tests/regression/ -v

# Run specific test file
python -m pytest tests/regression/test_rate_limiting.py -v

# Run with regression marker only
python -m pytest -m regression -v
```

## Adding New Regression Tests

When adding new regression tests:

1. **Document the Original Issue**: Clearly describe what problem occurred
2. **Test the Fix**: Ensure the test validates the fix is working
3. **Keep It Simple**: Focus on essential functionality, avoid over-engineering
4. **Use Appropriate Markers**: Mark tests with `@pytest.mark.regression`
5. **Handle Graceful Failure**: Tests should verify graceful degradation, not just success

## Markers Used

- `@pytest.mark.regression`: Identifies regression tests
- `@pytest.mark.cache`: Redis/caching related tests
- `@pytest.mark.database`: Database/SQLAlchemy related tests
- `@pytest.mark.api`: External API related tests

These tests help ensure the system maintains its reliability and graceful error handling as it evolves.
