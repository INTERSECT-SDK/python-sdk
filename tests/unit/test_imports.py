import intersect_sdk


def test_imports() -> None:
    """Quick PEP-562 test, make sure every import is valid."""
    for attr in dir(intersect_sdk):
        assert getattr(intersect_sdk, attr) is not None
