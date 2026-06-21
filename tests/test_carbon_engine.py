from src.carbon_engine import (
    _detect_anomaly,
    classify_tier,
)

FIXTURE_PATH = "tests/fixtures/carbon_factors_fixture.csv"


def test_classify_tier():
    """Verify tier thresholds and data."""
    t1 = classify_tier(5000)
    assert t1.tier == "Human"

    t2 = classify_tier(12000)
    assert t2.tier == "Category 1 Warning"

    t3 = classify_tier(25000)
    assert t3.tier == "Category 2 Catastrophe"

    t4 = classify_tier(50000)
    assert t4.tier == "Category 3 Catastrophe"
    assert t4.color == "#ff4b4b"


def test_detect_anomaly_no_data(tmp_path):
    """Verify anomaly detection gracefully handles empty sessions."""
    test_db = str(tmp_path / "test.duckdb")

    # Empty db should not throw an anomaly
    assert _detect_anomaly("empty-session", 10.0, db_path=test_db) is False


def test_detect_anomaly_with_data(tmp_path):
    """Verify anomaly detection triggers on 90th percentile spikes."""
    from src.history import append_history

    test_db = str(tmp_path / "test.duckdb")

    # Seed normal days (around 10kg)
    for _ in range(10):
        append_history("spike-session", 10.0, "Human", db_path=test_db)

    # Anomaly test: 50kg is > 90th percentile (which is 10kg)
    assert _detect_anomaly("spike-session", 50.0, db_path=test_db) is True

    # Normal test: 5kg is <= 90th percentile
    assert _detect_anomaly("spike-session", 5.0, db_path=test_db) is False
