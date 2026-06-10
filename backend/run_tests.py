import pytest
import sys

if __name__ == "__main__":
    print("Starting test suite...")
    sys.exit(pytest.main(["tests/", "-v", "-s"]))
