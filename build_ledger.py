import duckdb

conn = duckdb.connect()
query = """
COPY (
    SELECT
        h.instance_type,
        h.vcpus,
        h.min_watts,
        h.max_watts,
        h.cost_per_hour_usd,
        g.region,
        g.grid_name,
        g.carbon_intensity_kg_per_kwh,
        ((h.max_watts * 24) / 1000.0) * g.carbon_intensity_kg_per_kwh AS co2_per_day_kg
    FROM read_csv_auto('data/ccf_hardware_baseline.csv') h
    CROSS JOIN read_csv_auto('data/epa_egrid_intensity.csv') g
) TO 'data/sre_consolidated_ledger.csv' (HEADER, DELIMITER ',');
"""
conn.execute(query)
print("Successfully generated data/sre_consolidated_ledger.csv")
