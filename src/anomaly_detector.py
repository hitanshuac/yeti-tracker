"""
Anomaly Detection Engine using scikit-learn Isolation Forest.
Dynamically infers carbon baselines from historical data and flags behavioral spikes.
"""

import duckdb
import numpy as np
from sklearn.ensemble import IsolationForest

from src.capabilities.observability import log_error


def _fetch_history(session_id: str, db_path: str):
    """Helper to fetch history safely."""
    try:
        conn = duckdb.connect(db_path)
        df = conn.execute(
            "SELECT daily_carbon_kg FROM user_history WHERE session_id = ? ORDER BY timestamp DESC LIMIT 30",
            [session_id],
        ).fetchdf()
        conn.close()
        return df
    except (duckdb.Error, OSError) as e:
        log_error(e, "anomaly_detector", f"Failed to fetch history from DuckDB: {e!s}")
        return None
    except Exception as e:
        log_error(e, "anomaly_detector", f"Unexpected error connecting to DuckDB: {e!s}")
        return None


def detect_anomaly_and_baseline(session_id: str, db_path: str = "data/yeti.duckdb") -> tuple[float, bool]:
    """
    Analyzes user history using an Isolation Forest.

    Args:
        session_id: The UUID of the user session.
        db_path: Path to the duckdb file.

    Returns:
        tuple[float, bool]: The dynamically calculated yearly baseline (min 1500.0),
                            and a boolean indicating if the most recent entry is an anomaly.
    """
    df = _fetch_history(session_id, db_path)
    if df is None or len(df) < 5:
        # Not enough data to confidently detect anomalies
        return 1500.0, False

    # Reverse to chronological order
    df = df.iloc[::-1].reset_index(drop=True)
    features = df[["daily_carbon_kg"]].values

    try:
        # Fit Isolation Forest
        iso = IsolationForest(contamination=0.1, random_state=42)
        predictions = iso.fit_predict(features)

        # predictions: -1 is anomaly, 1 is inlier
        is_anomaly = bool(predictions[-1] == -1)

        # Baseline is the median of INLIER data
        inliers = features[predictions == 1]
        if len(inliers) > 0:
            daily_median = float(np.median(inliers))
            yearly_baseline = daily_median * 365.0
            # Ensure dynamic baseline never falls below the absolute infrastructure floor
            dynamic_baseline = max(1500.0, yearly_baseline)
        else:
            dynamic_baseline = 1500.0

        return dynamic_baseline, is_anomaly

    except Exception as e:
        # Fallback to static if ML engine fails
        log_error(e, "anomaly_detector", f"IsolationForest failed: {e!s}")
        return 1500.0, False
