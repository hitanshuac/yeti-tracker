import csv
import json
import uuid
import os

CSV_FILE = "data/personal_carbon_footprint_sample.csv"
OUTPUT_DIR = "data/raw_transactions"

def generate_transactions_from_csv():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    transactions = []
    
    with open(CSV_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        idx = 0
        
        for idx, row in enumerate(reader):
            date_str = row['date']
            timestamp = f"{date_str}T12:00:00.000Z"
            user_id = "user_csv_01"
            
            # Transport
            dist = float(row['distance_km'])
            t_mode = row['transport_mode']
            if dist > 0:
                if t_mode in ['Bus', 'EV']:
                    transactions.append({
                        "transaction_id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "mcc": "4111", # Local Commuter Transport
                        "amount_inr": round(dist * 15, 2),
                        "timestamp": timestamp
                    })
                elif t_mode == 'Car':
                    transactions.append({
                        "transaction_id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "mcc": "5541", # Gas Station
                        "amount_inr": round(dist * 10, 2),
                        "timestamp": timestamp
                    })
            
            # Food
            food = row['food_type']
            food_cost = 500 if food == 'Veg' else (750 if food == 'Mixed' else 1000)
            transactions.append({
                "transaction_id": str(uuid.uuid4()),
                "user_id": user_id,
                "mcc": "5411" if food == 'Veg' else "5812", # Groceries or Restaurant
                "amount_inr": float(food_cost),
                "timestamp": timestamp
            })
            
            # Electricity
            elec = float(row['electricity_kwh'])
            if elec > 0:
                transactions.append({
                    "transaction_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "mcc": "4900", # Utility
                    "amount_inr": round(elec * 8, 2),
                    "timestamp": timestamp
                })
                
    batch_id = str(uuid.uuid4())
    file_path = os.path.join(OUTPUT_DIR, f"batch_csv_{batch_id}.json")
    
    with open(file_path, "w") as f:
        json.dump(transactions, f, indent=4)
        
    print(f"Successfully converted {idx+1} CSV rows into {len(transactions)} mock transactions.")
    print(f"Payload saved to {file_path}")

if __name__ == "__main__":
    generate_transactions_from_csv()
