import pytest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Set test environment
os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["JWT_SECRET"] = "test-secret-minimum-32-characters-long"
