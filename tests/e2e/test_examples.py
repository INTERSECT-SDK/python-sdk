"""
These E2E tests are based off of the examples. This does not entirely mirror
a "true" production instance, but does require the following components:
- one IntersectClient
- one or more IntersectServers
- one instance of each data service needed for INTERSECT
- one instance of a broker

To run the E2E tests, you will need a broker + backing services running.

TODO these may not work on Windows or Mac
"""

import glob
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = (
    Path(os.path.sep.join(os.path.dirname(os.path.abspath(__file__)).split(os.path.sep)[:-2]))
    / 'examples'
)


# HELPERS #####################


# TODO - run all files as modules
def run_example_test(example: str, timeout: int = 60) -> str:
    example_dir = BASE_DIR / example
    service_files = glob.glob(f'{example_dir}{os.path.sep}*_service.py')
    client_file = glob.glob(f'{example_dir}{os.path.sep}*_client.py')[0]
    service_procs = [subprocess.Popen([sys.executable, file]) for file in service_files]  # noqa: S603 (make sure repository is arranged such that this command is safe to run)
    # make sure all service processes have been initialized before starting client process
    time.sleep(1.0)
    client_output = subprocess.run(
        [sys.executable, client_file],  # noqa: S603
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    try:
        assert client_output.returncode == 0
        return client_output.stdout
    finally:
        for proc in service_procs:
            os.kill(proc.pid, signal.SIGINT)


# TESTS ######################


def test_example_1_hello_world_amqp():
    assert run_example_test('1_hello_world_amqp') == 'Hello, hello_client!\n'


def test_example_1_hello_world_mqtt():
    assert run_example_test('1_hello_world') == 'Hello, hello_client!\n'


def test_example_2_counter():
    actual_stdout = run_example_test('2_counting')
    assert (
        actual_stdout
        == """Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
Operation: start_count
Payload: {'state': {'count': 1, 'counting': True}, 'success': True}

Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
Operation: stop_count
Payload: {'state': {'count': 6, 'counting': False}, 'success': True}

Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
Operation: start_count
Payload: {'state': {'count': 7, 'counting': True}, 'success': True}

Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
Operation: reset_count
Payload: {'count': 10, 'counting': True}

Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
Operation: reset_count
Payload: {'count': 6, 'counting': True}

Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
Operation: start_count
Payload: {'state': {'count': 1, 'counting': True}, 'success': True}

Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
Operation: stop_count
Payload: {'state': {'count': 4, 'counting': False}, 'success': True}

"""
    )
