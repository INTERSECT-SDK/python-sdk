# Changelog

We follow [Common Changelog](https://common-changelog.org/) formatting for this document.

## [0.8.4] - 2026-02-05

### Fixed

- Fixed an issue with JSON schema resolution ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/f4e51ffae0ad94cd12387d664d019afa6cf790c0)) (Lance Drane, Shayan Monadjemi)

## [0.8.3] - 2025-05-27

### Fixed

- (AMQP): Services using `@intersect_message` endpoints + Clients should now be able to execute long-running tasks without causing disconnects. AMQP message consumers no longer block the AMQP I/O loop, but now handle messages in their own threads; this allows the AMQP I/O loop to continue sending heartbeat frames to the remote broker, preventing the broker from disconnecting the microservice. ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/a9f9d110da924ec423ac42e5c316475a7d8e1f3e)) (Lance Drane)

## [0.8.2] - 2025-02-21

### Changed

- Capabilities will now pass validation if they only contain a valid `@intersect_status` ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/dd41396ec5cb78982ed844e15e43257842e07f7d)) (Lance Drane)

### Fixed

- Do not allow for users to override the `BaseCapability.intersect_sdk_listen_for_service_event` function ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/387e0d2b134de6c52cbe54a51ff99b9245432335))
- Add missing schemas for service-to-service event example ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/e52902fadf80c2dcbcc79552fcba005d565b57ea))

## [0.8.1] - 2025-02-10

### Changed

- Events associated with Services are now considered to be persistent. If your microservice loses INTERSECT connection and later regains it, it will now handle any events which occurred while disconnected from INTERSECT ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/b57d72022f8fc8fb1c25e7985eaf4e18ed2d1904)) (Lance Drane)

### Added

- Added ability for services to listen for events from other services ([issue](https://github.com/INTERSECT-SDK/python-sdk/issues/20)) ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/b57d72022f8fc8fb1c25e7985eaf4e18ed2d1904)) (Lance Drane)

## [0.8.0] - 2024-09-10

_If you are upgrading: please see [`UPGRADING.md`](UPGRADING.md)._

### Changed

- **Breaking:** Service-to-service callback functions now take in four arguments (request message source, request message operation, error flag, response payload) instead of one ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/51ba9a8e0eb8c314014655bb0c989f5f98db715d)) (Lance Drane)
- **Breaking:** `IntersectBaseCapabilityImplementation.capability_name` renamed to `IntersectBaseCapabilityImplementation.intersect_sdk_capability_name`. This should now be explicitly defined as a class variable instead of an instance variable ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/1753a2cce1344a101c7cc41f91c6ed3467b1be52)) (Lance Drane)
- **Breaking:** `get_schema_from_capability_implementation` renamed to `get_schema_from_capability_implementations` and now takes in a list of Capabilities instead of a single capability ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/1753a2cce1344a101c7cc41f91c6ed3467b1be52)) (Lance Drane)

### Fixed

- Fixed issue with multiple service-to-service calls causing thread deadlocking ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/51ba9a8e0eb8c314014655bb0c989f5f98db715d)) (Lance Drane)
- Correctly incorporates capabilities into internal schema generation ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/1753a2cce1344a101c7cc41f91c6ed3467b1be52)) (Lance Drane)
- Removed MINIO from examples which do not use MINIO ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/1753a2cce1344a101c7cc41f91c6ed3467b1be52)) (Lance Drane)

### Added

- **Breaking:** Added basic validation logic for capability names. This causes the application to error out if using a duplicate capability name, or if using a capability name which is not an alphanumeric string (hyphens and underscores allowed) ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/1753a2cce1344a101c7cc41f91c6ed3467b1be52)) (Lance Drane)
- Added 'timeout' parameter to `IntersectBaseCapabilityImplementation.intersect_sdk_call_service`. This is a floating point value which represents (in number of seconds) how long to wait for a response from the service. By default, the service will wait 300 seconds ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/51ba9a8e0eb8c314014655bb0c989f5f98db715d)) (Lance Drane)
- Added an example which uses MINIO ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/1753a2cce1344a101c7cc41f91c6ed3467b1be52)) (Lance Drane)

## [0.7.0] - 2024-08-21

_If you are upgrading: please see [`UPGRADING.md`](UPGRADING.md)._

### Changed

- **Breaking:** Services now work with multiple Capabilities instead of a single Capability ([!9](https://github.com/INTERSECT-SDK/python-sdk/pull/9)) (Michael Brim, Lance Drane)
- **Breaking:** Renamed `IntersectClientMessageParams` to `IntersectDirectMessageParams` ([commit](https://github.com/INTERSECT-SDK/python-sdk/commit/ae0dab312b9ebdb87bc5a9bb62404d9b18953dfe)) (Lance Drane)

### Added

- **Breaking:** Added service-to-service request/response mechanism ([!9](https://github.com/INTERSECT-SDK/python-sdk/pull/9)) (Michael Brim, Lance Drane)

[0.8.3]: https://github.com/INTERSECT-SDK/python-sdk/releases/tag/0.8.3
[0.8.2]: https://github.com/INTERSECT-SDK/python-sdk/releases/tag/0.8.2
[0.8.1]: https://github.com/INTERSECT-SDK/python-sdk/releases/tag/0.8.1
[0.8.0]: https://github.com/INTERSECT-SDK/python-sdk/releases/tag/0.8.0
[0.7.0]: https://github.com/INTERSECT-SDK/python-sdk/releases/tag/0.7.0
