import mysql.connector
import random
from faker import Faker
import time

fake = Faker()

# MySQL Connection
db = mysql.connector.connect(
  unix_socket="/var/run/mysqld/mysqld.sock",  
  user="root",
  password="",
  database="esewa_db"
)
cursor = db.cursor()

print("🚀 Starting eSewa SRE Stress Test: Injecting 10,000 Transactions...")
start_time = time.time()

insert_query = "INSERT INTO wallet_txns (type, amount, nameOrig, nameDest, isFraud) VALUES (%s, %s, %s, %s, %s)"

# 10 Batches of 1000 records
for i in range(10):
    batch_data = []
    for _ in range(1000):
        txn_type = random.choice(['CASH_IN', 'CASH_OUT', 'TRANSFER', 'PAYMENT'])
        amount = round(random.uniform(10.0, 100000.0), 2) # Random amount up to 1 lakh
        nameOrig = fake.bothify(text='C#########')
        nameDest = fake.bothify(text='M#########')
        isFraud = 0
        batch_data.append((txn_type, amount, nameOrig, nameDest, isFraud))

    cursor.executemany(insert_query, batch_data)
    db.commit()
    print(f"✅ Batch {i+1}/10: 1000 records injected!")

end_time = time.time()
print(f"🏁 Stress Test Complete! 10,000 records inserted in {round(end_time - start_time, 2)} seconds.")