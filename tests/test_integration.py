import json
import shutil

from src.capabilities.observability import log_error


def test_log_error_integration(tmp_path):
    """
    State-Aware Integration Test.
    Verifies that log_error safely appends to an existing log file
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
    test_error = ValueError("This is a test error")
    log_error(test_error, "test_integration", error_logs_path=str(test_log_file))

    # 4. Read the final state and verify no data was lost
    with open(test_log_file, encoding="utf-8") as f:
        final_data = json.load(f)

    assert len(final_data) == initial_count + 1
    assert final_data[-1]["error_type"] == "ValueError"
    assert final_data[-1]["message"] == "This is a test error"
