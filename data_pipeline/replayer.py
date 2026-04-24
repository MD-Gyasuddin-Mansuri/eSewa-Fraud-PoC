import csv
import time
import mysql.connector

print("🚀 Connecting to MySQL...")
db = mysql.connector.connect(
    host="localhost",
    user="debezium_user",                
    password="eSewaStrongPass123!",    
    database="esewa_db"
)
cursor = db.cursor()

csv_file_path = 'paysim.csv'

try:
    with open(csv_file_path, 'r') as file:
        reader = csv.DictReader(file)
        print("✅ Connected! Starting eSewa Live Transaction Stream...")

        for row in reader:
            sql = """INSERT INTO live_wallet_txns
                     (step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig, nameDest, isFraud)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""

            val = (row['step'], row['type'], row['amount'], row['nameOrig'],
                   row['oldbalanceOrg'], row['newbalanceOrig'], row['nameDest'], row['isFraud'])

            cursor.execute(sql, val)
            db.commit()

            print(f"💸 Txn Inserted: {row['type']} of Rs {row['amount']} by {row['nameOrig']}")

            # 0.1 second wait garne to simulate live traffic
            time.sleep(0.1)

except FileNotFoundError:
    print("❌ Error: 'paysim.csv' file vetiena! Kripaya Kaggle data yehi folder ma halnus.")