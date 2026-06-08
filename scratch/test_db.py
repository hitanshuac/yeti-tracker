import duckdb

conn = duckdb.connect()
print("--- DIET ---")
print(conn.execute("SELECT food_type, AVG(carbon_footprint_kg) FROM read_csv_auto('data/personal_carbon_footprint_sample.csv') GROUP BY food_type").df())

print("--- TRANSPORT ---")
print(conn.execute("SELECT transport_mode, AVG(carbon_footprint_kg) FROM read_csv_auto('data/personal_carbon_footprint_sample.csv') GROUP BY transport_mode").df())

print("--- ELECTRICITY ---")
print(conn.execute("SELECT CASE WHEN electricity_kwh < 10 THEN 'Low' WHEN electricity_kwh BETWEEN 10 AND 20 THEN 'Medium' ELSE 'High' END as tier, AVG(carbon_footprint_kg) FROM read_csv_auto('data/personal_carbon_footprint_sample.csv') GROUP BY tier").df())
