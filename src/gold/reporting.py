import duckdb
from typing import List, Dict, Any

DB_PATH = "data/yeti.duckdb"

def get_user_footprint(user_id: str) -> Dict[str, Any]:
    """Returns the aggregated carbon footprint for a specific user."""
    conn = duckdb.connect(DB_PATH)
    conn.execute("PRAGMA memory_limit='2GB'")
    
    query = """
        SELECT 
            user_id,
            SUM(carbon_kg) as total_carbon_kg,
            COUNT(transaction_id) as total_transactions
        FROM silver_transactions
        WHERE user_id = ?
        GROUP BY user_id
    """
    
    result = conn.execute(query, [user_id]).fetchone()
    conn.close()
    
    if result:
        return {
            "user_id": result[0],
            "total_carbon_kg": round(result[1], 4),
            "total_transactions": result[2]
        }
    return {"user_id": user_id, "total_carbon_kg": 0.0, "total_transactions": 0}

def get_category_footprint() -> List[Dict[str, Any]]:
    """Returns the total carbon footprint grouped by category across all users."""
    conn = duckdb.connect(DB_PATH)
    conn.execute("PRAGMA memory_limit='2GB'")
    
    query = """
        SELECT 
            category,
            SUM(carbon_kg) as total_carbon_kg,
            COUNT(transaction_id) as total_transactions
        FROM silver_transactions
        GROUP BY category
        ORDER BY total_carbon_kg DESC
    """
    
    results = conn.execute(query).fetchall()
    conn.close()
    
    return [
        {
            "category": row[0],
            "total_carbon_kg": round(row[1], 4),
            "total_transactions": row[2]
        }
        for row in results
    ]
