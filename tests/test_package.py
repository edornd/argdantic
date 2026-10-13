import argdantic


def test_version_is_exposed() -> None:
    assert argdantic.__version__ == "2.0.0.dev0"
