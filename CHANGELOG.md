# Changelog

## Unreleased

## [0.8.0] - 2024-09-10

_If you are upgrading: please see [`UPGRADING.md`](UPGRADING.md)._

### Changed

- **Breaking:** Service-to-service callback functions now take in four arguments (request message source, request message operation, error flag, response payload) instead of one ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/51ba9a8e0eb8c314014655bb0c989f5f98db715d)) .
- **Breaking:** `IntersectBaseCapabilityImplementation.capability_name` renamed to `IntersectBaseCapabilityImplementation.intersect_sdk_capability_name`. This should now be explicitly defined as a class variable instead of an instance variable ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/1753a2cce1344a101c7cc41f91c6ed3467b1be52)) .
- **Breaking:** `get_schema_from_capability_implementation` renamed to `get_schema_from_capability_implementations` and now takes in a list of Capabilities instead of a single capability ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/1753a2cce1344a101c7cc41f91c6ed3467b1be52)) .

### Fixed

- Fixed issue with multiple service-to-service calls causing thread deadlocking ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/51ba9a8e0eb8c314014655bb0c989f5f98db715d)) .
- Correctly incorporates capabilities into internal schema generation ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/1753a2cce1344a101c7cc41f91c6ed3467b1be52)) .
- Removed MINIO from examples which do not use MINIO ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/1753a2cce1344a101c7cc41f91c6ed3467b1be52)) .

### Added

- **Breaking:** Added basic validation logic for capability names. This causes the application to error out if using a duplicate capability name, or if using a capability name which is not an alphanumeric string (hyphens and underscores allowed) ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/1753a2cce1344a101c7cc41f91c6ed3467b1be52)) .
- Added 'timeout' parameter to `IntersectBaseCapabilityImplementation.intersect_sdk_call_service`. This is a floating point value which represents (in number of seconds) how long to wait for a response from the service. By default, the service will wait 300 seconds ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/51ba9a8e0eb8c314014655bb0c989f5f98db715d)) .
- Added an example which uses MINIO ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/1753a2cce1344a101c7cc41f91c6ed3467b1be52)) .

## [0.7.0] - 2024-08-21

_If you are upgrading: please see [`UPGRADING.md`](UPGRADING.md)._

### Changed

- **Breaking:** Services now work with multiple Capabilities instead of a single Capability ([!9](https://github.com/INTERSECT-SDK/python-sdk/pull/9)) .
- **Breaking:** Renamed `IntersectClientMessageParams` to `IntersectDirectMessageParams` ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/ae0dab312b9ebdb87bc5a9bb62404d9b18953dfe))

### Added

- **Breaking:** Added service-to-service request/response mechanism ([!9](https://github.com/INTERSECT-SDK/python-sdk/pull/9)) .

[0.8.0]: https://github.com/Level/level/releases/tag/0.8.0
[0.7.0]: https://github.com/Level/level/releases/tag/0.7.0
