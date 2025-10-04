#!/bin/bash
# Comprehensive test suite runner for regression and feature testing
# Runs all tests with detailed reporting

set -e

echo "======================================"
echo "   Full Regression Test Suite"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}pytest not found. Installing...${NC}"
    pip install pytest pytest-cov pytest-html
fi

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null && ! nc -z localhost 6379 2>/dev/null; then
    echo -e "${YELLOW}Warning: Redis doesn't appear to be running.${NC}"
    echo "RQ tests may fail. Start Redis with: redis-server"
    echo ""
fi

echo -e "${GREEN}Starting test suite...${NC}"
echo ""

# Create reports directory
mkdir -p test_reports

# Run unit tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1. Unit Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
pytest tests/unit/ -v --tb=short --html=test_reports/unit_tests.html --self-contained-html
UNIT_EXIT=$?

# Run integration tests  
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  2. Integration Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
pytest tests/integration/ -v --tb=short --html=test_reports/integration_tests.html --self-contained-html
INTEGRATION_EXIT=$?

# Run RQ-specific tests
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  3. RQ Background Job Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
pytest tests/integration/test_rq_background_jobs.py -v --tb=short --html=test_reports/rq_tests.html --self-contained-html
RQ_EXIT=$?

# Run regression suite
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  4. Regression Test Suite"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
pytest tests/integration/test_regression_suite.py -v --tb=short --html=test_reports/regression_tests.html --self-contained-html
REGRESSION_EXIT=$?

# Run queue helper tests
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  5. Queue Helper Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
pytest tests/test_queue_helpers.py -v --tb=short --html=test_reports/queue_helper_tests.html --self-contained-html
QUEUE_EXIT=$?

# Run all tests with coverage
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  6. Full Coverage Report"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
pytest tests/ --cov=app --cov-report=html:test_reports/coverage --cov-report=term-missing --html=test_reports/full_suite.html --self-contained-html
COVERAGE_EXIT=$?

# Summary
echo ""
echo "======================================"
echo "   Test Summary"
echo "======================================"
echo ""

if [ $UNIT_EXIT -eq 0 ]; then
    echo -e "✅ ${GREEN}Unit Tests:        PASSED${NC}"
else
    echo -e "❌ ${RED}Unit Tests:        FAILED${NC}"
fi

if [ $INTEGRATION_EXIT -eq 0 ]; then
    echo -e "✅ ${GREEN}Integration Tests: PASSED${NC}"
else
    echo -e "❌ ${RED}Integration Tests: FAILED${NC}"
fi

if [ $RQ_EXIT -eq 0 ]; then
    echo -e "✅ ${GREEN}RQ Tests:          PASSED${NC}"
else
    echo -e "❌ ${RED}RQ Tests:          FAILED${NC}"
fi

if [ $REGRESSION_EXIT -eq 0 ]; then
    echo -e "✅ ${GREEN}Regression Tests:  PASSED${NC}"
else
    echo -e "❌ ${RED}Regression Tests:  FAILED${NC}"
fi

if [ $QUEUE_EXIT -eq 0 ]; then
    echo -e "✅ ${GREEN}Queue Tests:       PASSED${NC}"
else
    echo -e "❌ ${RED}Queue Tests:       FAILED${NC}"
fi

echo ""
echo "📊 Test reports saved to: test_reports/"
echo "   - Coverage report: test_reports/coverage/index.html"
echo "   - Full report:     test_reports/full_suite.html"
echo ""

# Overall exit code
if [ $UNIT_EXIT -eq 0 ] && [ $INTEGRATION_EXIT -eq 0 ] && [ $RQ_EXIT -eq 0 ] && [ $REGRESSION_EXIT -eq 0 ] && [ $QUEUE_EXIT -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}   ALL TESTS PASSED! ✨${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}   SOME TESTS FAILED ❌${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
fi

