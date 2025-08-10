"""Configure pytest with extra options."""

import shutil
from pathlib import Path


def pytest_addoption(parser):
    """Add ci option (running on github) to the parser."""
    parser.addoption("--cirunner", action="store_true", default=False)


import pytest  # noqa: E402


@pytest.fixture
def cirunner(request):
    """Allow to inject a bool to test functions."""
    return request.config.getoption("--cirunner")


@pytest.fixture(scope="function", autouse=True)
def remvove_generated_test_files():
    """
    Remove all files generated during a test.

    The 'function' scope makes it run after every single test function
    and 'autotuse' lets it run without the requirement to mark the
    functions.
    """
    exec_path = Path.cwd()
    original_files = set(exec_path.glob("*"))
    yield
    files_after_finish = set(exec_path.glob("*"))
    diff = files_after_finish - original_files
    for file in diff:
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            shutil.rmtree(file)
