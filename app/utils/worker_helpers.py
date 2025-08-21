"""
Test helper functions for RQ worker verification
"""


def worker_test_job() -> str:
    """Simple test function to verify RQ worker is running"""
    return "RQ Worker is running successfully!"


def simple_addition(a: int, b: int) -> int:
    """Simple math function for testing worker execution"""
    return a + b
