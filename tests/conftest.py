import pytest

from argdantic.testing import CLIRunner


@pytest.fixture(scope="function")
def runner():
    return CLIRunner()
