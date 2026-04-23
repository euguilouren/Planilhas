"""pytest configuration and shared fixtures."""
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: tests that take more than 1 second")
    config.addinivalue_line("markers", "integration: tests that require file I/O")
