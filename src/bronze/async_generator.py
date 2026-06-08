import asyncio
import json
import random
import uuid
import os
from datetime import datetime

OUTPUT_DIR = "data/raw_transactions"

# List of Merchant Category Codes we have mapped
MCCS = ["4111", "4511", "4900", "5411", "5541", "5812", "5691"]

async def simulate_transaction():
    """Simulates a single live transaction payload."""
    transaction = {
        "transaction_id": str(uuid.uuid4()),
        "user_id": f"user_{random.randint(1, 100)}",
        "mcc": random.choice(MCCS),
        "amount_inr": round(random.uniform(50.0, 5000.0), 2),
        "timestamp": datetime.now().isoformat()
    }
    return transaction

async def async_generator(num_transactions: int = 50, batch_delay: float = 0.1):
    """
    Generates asynchronous mock transactions and writes them to the Bronze layer raw directory.
    Uses asyncio to simulate high-throughput real-time ingestion.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print(f"Starting async generation of {num_transactions} transactions...")
    
    tasks = []
    for _ in range(num_transactions):
        tasks.append(simulate_transaction())
        await asyncio.sleep(batch_delay) # Simulate slight latency between events
        
    transactions = await asyncio.gather(*tasks)
    
    # Save batch to a single JSON file for bronze ingestion
    batch_id = str(uuid.uuid4())
    file_path = os.path.join(OUTPUT_DIR, f"batch_{batch_id}.json")
    
    with open(file_path, "w") as f:
        json.dump(transactions, f, indent=4)
        
    print(f"Successfully generated {len(transactions)} mock transactions.")
    print(f"Payload saved safely out of Git tracking at: {file_path}")

if __name__ == "__main__":
    # Simulate a burst of 20 live transactions
    asyncio.run(async_generator(num_transactions=20, batch_delay=0.05))
