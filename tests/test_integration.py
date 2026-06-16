import json
import shutil

from app import log_error_to_json


def test_log_error_to_json_integration(tmp_path):
    """
    State-Aware Integration Test.
    Verifies that log_error_to_json safely appends to an existing log file
    without corrupting data, ensuring idempotent file operations.
    """
    # 1. Setup the fixture in a temporary safe location
    fixture_src = "tests/fixtures/error_logs_sample.json"
    test_log_file = tmp_path / "error_logs.json"
    shutil.copy(fixture_src, test_log_file)

    # 2. Read the initial state
    with open(test_log_file, encoding="utf-8") as f:
        initial_data = json.load(f)
    initial_count = len(initial_data)

    # 3. Perform the operation using the injected path
    log_error_to_json("TestError", "test_integration", "This is a test error", log_file=str(test_log_file))

    # 4. Read the final state and verify no data was lost
    with open(test_log_file, encoding="utf-8") as f:
        final_data = json.load(f)

    assert len(final_data) == initial_count + 1
    assert final_data[-1]["error_type"] == "TestError"
    assert final_data[-1]["message"] == "This is a test error"
