import pandas as pd # type: ignore
import mysql.connector
import time
import sys

print("🔌 Connecting to MySQL (Source DB)...")
try:
    db = mysql.connector.connect(
        host="localhost",
        user="fraud_engine",
        password="EnginePass123!",
        database="esewa_db"
    )
    cursor = db.cursor()
    print("✅ Connected successfully!")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    sys.exit()

print("📂 Loading PaySim Dataset (First 10,000 rows)...")
try:
    # Reading only 10,000 rows for the PoC load test
    df = pd.read_csv('paysim.csv', nrows=10000)
except FileNotFoundError:
    print("❌ Error: 'paysim.csv' not found! Make sure the file is in the same folder.")
    sys.exit()

print(f"🚀 Starting to inject {len(df)} transactions into the eSewa Pipeline...")
print("-" * 50)

for index, row in df.iterrows():
    sql = """INSERT INTO live_wallet_txns
             (step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig, nameDest, isFraud)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""

    values = (
        int(row['step']),
        str(row['type']),
        float(row['amount']),
        str(row['nameOrig']),
        float(row['oldbalanceOrg']),
        float(row['newbalanceOrig']),
        str(row['nameDest']),
        0  # Initially setting all to 0, let the AI catch the real fraud!
    )

    try:
        cursor.execute(sql, values)
        db.commit()

        # Print progress every 100 transactions
        if index > 0 and index % 100 == 0:
            print(f"⚡ Injected {index} transactions...")

        # The SRE Magic: Simulate real-world gateway delay (2 txns per second)
        time.sleep(0.5)

    except Exception as e:
        print(f"⚠️ Warning: Failed to inject row {index} -> {e}")

print("-" * 50)
print("🏁 Load Test Complete! Check Grafana and ClickHouse to see the results.")

cursor.close()
db.close()