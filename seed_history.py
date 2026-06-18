import random
from datetime import datetime, timedelta

import duckdb


def seed_database(db_path="data/yeti.duckdb"):
    print(f"Connecting to DuckDB at {db_path}...")
    conn = duckdb.connect(db_path)

    # Clear existing demo data so this script is idempotent
    conn.execute("DROP TABLE IF EXISTS user_history")

    # Create schema idempotently
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_history (
            session_id VARCHAR,
            timestamp TIMESTAMP,
            daily_carbon_kg DOUBLE,
            tier VARCHAR
        )
    """)

    print("Seeding 30 days of historical data for 'demo_user'...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    current_date = start_date
    base_carbon = 20.0  # kg per day starting point

    while current_date <= end_date:
        # Add a slight upward trend and some random noise
        base_carbon += random.uniform(0.1, 1.5)
        daily_val = base_carbon + random.uniform(-5.0, 10.0)

        # Determine tier (just for logging context)
        yearly_projection = daily_val * 365
        if yearly_projection > 30000:
            tier = "Category 3 Catastrophe"
        elif yearly_projection > 15000:
            tier = "Category 2 Catastrophe"
        elif yearly_projection > 9000:
            tier = "Category 1 Catastrophe"
        else:
            tier = "Human"

        conn.execute("INSERT INTO user_history VALUES (?, ?, ?, ?)", ["demo_user", current_date, daily_val, tier])
        current_date += timedelta(days=1)

    print("Seed complete!")


if __name__ == "__main__":
    import os

    os.makedirs("data", exist_ok=True)
    seed_database()
