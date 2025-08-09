"""Configure pytest with extra options."""


def pytest_addoption(parser):
    """Add ci option (running on github) to the parser."""
    parser.addoption("--cirunner", action="store_true", default=False)


import pytest  # noqa: E402


@pytest.fixture
def cirunner(request):
    """Allow to inject a bool to test functions."""
    return request.config.getoption("--cirunner")
