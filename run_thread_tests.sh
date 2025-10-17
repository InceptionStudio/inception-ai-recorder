#!/bin/bash
# Test runner for thread health tests

set -e

echo "=================================================="
echo "Thread Health Test Suite Runner"
echo "=================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
    else
        echo -e "${RED}✗ FAILED${NC}"
    fi
}

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: No virtual environment detected${NC}"
    echo "Consider activating your virtual environment first:"
    echo "  source venv/bin/activate"
    echo ""
fi

# Parse command line arguments
TEST_CATEGORY="${1:-all}"

case "$TEST_CATEGORY" in
    "all")
        echo "Running all thread health tests..."
        echo ""
        python test_thread_health.py
        TEST_RESULT=$?
        ;;

    "health")
        echo "Running thread health lifecycle tests..."
        echo ""
        python -m unittest test_thread_health.TestThreadHealth -v
        TEST_RESULT=$?
        ;;

    "recovery")
        echo "Running thread recovery tests..."
        echo ""
        python -m unittest test_thread_health.TestThreadRecovery -v
        TEST_RESULT=$?
        ;;

    "edge")
        echo "Running edge case tests..."
        echo ""
        python -m unittest test_thread_health.TestThreadEdgeCases -v
        TEST_RESULT=$?
        ;;

    "quick")
        echo "Running quick thread health tests (excludes slow recovery tests)..."
        echo ""
        python -m unittest \
            test_thread_health.TestThreadHealth.test_thread_starts_when_device_selected \
            test_thread_health.TestThreadHealth.test_thread_stops_when_device_deselected \
            test_thread_health.TestThreadHealth.test_thread_processes_audio_data \
            test_thread_health.TestThreadHealth.test_health_monitor_running \
            -v
        TEST_RESULT=$?
        ;;

    "monitor")
        echo "Running health monitor detection test..."
        echo "(This test takes ~15 seconds to wait for recovery)"
        echo ""
        python -m unittest test_thread_health.TestThreadHealth.test_health_monitor_detects_dead_thread -v
        TEST_RESULT=$?
        ;;

    "help"|"-h"|"--help")
        echo "Usage: $0 [category]"
        echo ""
        echo "Categories:"
        echo "  all       - Run all tests (default)"
        echo "  health    - Run basic thread lifecycle tests"
        echo "  recovery  - Run auto-recovery tests"
        echo "  edge      - Run edge case tests"
        echo "  quick     - Run fast tests only (skip recovery tests)"
        echo "  monitor   - Run health monitor detection test"
        echo "  help      - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0              # Run all tests"
        echo "  $0 quick        # Run quick tests"
        echo "  $0 recovery     # Run recovery tests"
        exit 0
        ;;

    *)
        echo -e "${RED}Error: Unknown test category '$TEST_CATEGORY'${NC}"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac

echo ""
echo "=================================================="
echo -n "Test Result: "
print_status $TEST_RESULT
echo "=================================================="

exit $TEST_RESULT
