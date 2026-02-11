"""
This tests possible SDK version resolutions.

These need to be isolated away from the integration/e2e tests
because these tests are also meant to work when comparing two SDK versions
which may differ from the CURRENT SDK version.

Note that there are some aspects of version_resolver which CANNOT be tested,
such as checking for data_handler and content_type incompatibilities
(but that's why we have the version check in the first place!)
"""

import pytest

from intersect_sdk import (
    IntersectDataHandler,
    version_info,
    version_string,
)
from intersect_sdk._internal.version_resolver import _resolve_user_version, resolve_user_version

# TESTS ##################


def test_version_info() -> None:
    assert len(version_info) == 3
    assert all(isinstance(x, int) for x in version_info)


# This section should contain tests using the public function, as we can test directly
# against THIS SDK's version


def test_equal_version_ok() -> None:
    assert resolve_user_version(version_string, 'source', IntersectDataHandler.MESSAGE) is True


def test_bugfix_up_ok() -> None:
    mock_version = f'{version_info[0]}.{version_info[1]}.{version_info[2] + 1}'
    assert resolve_user_version(mock_version, 'source', IntersectDataHandler.MESSAGE) is True


def test_bugfix_down_ok() -> None:
    mock_version = f'{version_info[0]}.{version_info[1]}.{version_info[2] - 1}'
    assert resolve_user_version(mock_version, 'source', IntersectDataHandler.MINIO) is True


def test_major_difference_up_not_ok(caplog: pytest.LogCaptureFixture) -> None:
    mock_version = f'{version_info[0] + 1}.{version_info[1]}.{version_info[2]}'
    assert resolve_user_version(mock_version, 'source', IntersectDataHandler.MESSAGE) is False
    assert 'Major version incompatibility' in caplog.text


def test_major_difference_down_not_ok(caplog: pytest.LogCaptureFixture) -> None:
    mock_version = f'{version_info[0] - 1}.{version_info[1]}.{version_info[2]}'
    assert resolve_user_version(mock_version, 'source', IntersectDataHandler.MESSAGE) is False
    assert 'Major version incompatibility' in caplog.text


# This section should contain tests using the PRIVATE function.
# We want to test against arbitrary SDK versions, which may not necessarily be this one.


def test_minor_version_up_ok_if_release() -> None:
    their_version = '1.1.0'
    our_version = '1.0.0'
    assert (
        _resolve_user_version(
            their_version,
            'their_source',
            IntersectDataHandler.MESSAGE,
            our_version,
            tuple([int(x) for x in our_version.split('.')]),
        )
        is True
    )


def test_minor_version_down_ok_if_release() -> None:
    their_version = '1.1.0'
    our_version = '1.2.0'
    assert (
        _resolve_user_version(
            their_version,
            'their_source',
            IntersectDataHandler.MESSAGE,
            our_version,
            tuple([int(x) for x in our_version.split('.')]),
        )
        is True
    )


def test_minor_version_up_not_ok_if_prerelease(caplog: pytest.LogCaptureFixture) -> None:
    their_version = '0.2.0'
    our_version = '0.1.0'
    assert (
        _resolve_user_version(
            their_version,
            'their_source',
            IntersectDataHandler.MESSAGE,
            our_version,
            tuple([int(x) for x in our_version.split('.')]),
        )
        is False
    )
    assert 'Pre-release minor version incompatibility' in caplog.text


def test_minor_version_down_not_ok_if_prerelease(caplog: pytest.LogCaptureFixture) -> None:
    their_version = '0.2.0'
    our_version = '0.3.0'
    assert (
        _resolve_user_version(
            their_version,
            'their_source',
            IntersectDataHandler.MESSAGE,
            our_version,
            tuple([int(x) for x in our_version.split('.')]),
        )
        is False
    )
    assert 'Pre-release minor version incompatibility' in caplog.text
