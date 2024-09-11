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

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

os.chdir(Path(__file__).parents[2])

# HELPERS #####################


def path_to_pymodule(p: Path) -> str:
    return str(p).replace(os.path.sep, '.')[:-3]


def run_example_test(example: str, timeout: int = 60) -> str:
    # convert all files to module syntax
    service_modules = [
        path_to_pymodule(f) for f in Path(f'examples/{example}/').glob('*_service.py')
    ]
    client_module = path_to_pymodule(next(Path(f'examples/{example}/').glob('*_client.py')))

    service_procs = [subprocess.Popen([sys.executable, '-m', file]) for file in service_modules]  # noqa: S603 (make sure repository is arranged such that this command is safe to run)
    # make sure all service processes have been initialized before starting client process
    time.sleep(1.0)
    try:
        client_output = subprocess.run(  # noqa: S603 (make sure repository is arranged such that this command is safe to run)
            [sys.executable, '-m', client_module],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
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


def test_example_1_hello_world_minio():
    assert run_example_test('1_hello_world_minio') == 'Hello, hello_client!\n'


def test_example_1_hello_world_events():
    assert (
        run_example_test('1_hello_world_events')
        == 'hello_client requested a salutation!\nHello, hello_client!\n'
    )


def test_example_2_counter():
    actual_stdout = run_example_test('2_counting')
    # the value of the actual counter can sometimes vary a little bit, don't fail the test if so
    lines = actual_stdout.splitlines()
    # test source
    for line_idx in range(0, len(lines), 4):
        assert (
            lines[line_idx]
            == 'Source: "counting-organization.counting-facility.counting-system.counting-subsystem.counting-service"'
        )
    # test operation
    assert lines[1] == 'Operation: "CountingExample.start_count"'
    assert lines[5] == 'Operation: "CountingExample.stop_count"'
    assert lines[9] == 'Operation: "CountingExample.start_count"'
    assert lines[13] == 'Operation: "CountingExample.reset_count"'
    assert lines[17] == 'Operation: "CountingExample.reset_count"'
    assert lines[21] == 'Operation: "CountingExample.start_count"'
    assert lines[25] == 'Operation: "CountingExample.stop_count"'

    # test payloads
    # if 'count' is within 3 steps of the subtrahend, just pass the test

    payload = json.loads(lines[2][9:])
    assert payload['state']['counting'] is True
    assert abs(payload['state']['count'] - 1) <= 3

    payload = json.loads(lines[6][9:])
    assert payload['state']['counting'] is False
    assert abs(payload['state']['count'] - 6) <= 3

    payload = json.loads(lines[10][9:])
    assert payload['state']['counting'] is True
    assert abs(payload['state']['count'] - 7) <= 3

    payload = json.loads(lines[14][9:])
    assert payload['counting'] is True
    assert abs(payload['count'] - 10) <= 3

    payload = json.loads(lines[18][9:])
    assert payload['counting'] is True
    assert abs(payload['count'] - 6) <= 3

    payload = json.loads(lines[22][9:])
    assert payload['state']['counting'] is True
    assert abs(payload['state']['count'] - 1) <= 3

    payload = json.loads(lines[26][9:])
    assert payload['state']['counting'] is False
    assert abs(payload['state']['count'] - 4) <= 3


def test_example_2_count_examples():
    assert run_example_test('2_counting_events') == '3\n9\n27\n'


def test_example_3_ping_pong_events():
    assert run_example_test('3_ping_pong_events') == 'ping\npong\nping\npong\n'


def test_example_3_ping_pong_events_amqp():
    assert run_example_test('3_ping_pong_events_amqp') == 'ping\npong\nping\npong\n'


def test_example_4_service_to_service():
    assert run_example_test('4_service_to_service') == (
        'Received Response from Service 2: Acknowledging service one text -> Kicking off the example!\n'
        'Received Second Response from Service 2: Acknowledging service one text -> Final Verification\n'
    )
