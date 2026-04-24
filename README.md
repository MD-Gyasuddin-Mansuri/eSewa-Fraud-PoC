# eSewa Real-Time Fraud Detection System: Architecture & Implementation Documentation

## 1. Project Overview & Architecture Objective

This project implements a High-Availability (HA), Real-Time Change Data Capture (CDC) pipeline integrated with an AI-driven fraud detection microservice. The architecture decouples operational transaction processing (OLTP) from heavy analytical workloads (OLAP) to evaluate a scalable, cost-effective alternative to unified databases (such as TiDB).

**The Data Pipeline Flow:**

1. **Transaction Source:** Python scripts inject high-throughput transaction data into a Native MySQL database via UNIX sockets.
    
2. **CDC Engine:** Debezium captures row-level changes from MySQL's binlog and streams them to an Apache Kafka topic.
    
3. **AI Microservice:** A Python-based Isolation Forest model consumes Kafka streams, evaluates transactions for anomalies (fraud), and logs the results.
    
4. **Data Warehouse:** A ClickHouse Distributed Cluster ingests the Kafka streams for ultra-low-latency aggregations.
    
5. **Observability:** Grafana connects to the ClickHouse cluster to provide a real-time Enterprise Command Center dashboard.
    

---

## 2. Infrastructure & Server Topology

The architecture is distributed across multiple instances to ensure fault tolerance and simulate a production-grade SRE environment.

|**Server Node**|**IP Address / Host**|**Components Running**|**Installation Method**|
|---|---|---|---|
|**esewa-mysql**|`localhost` / EC2|MySQL (Source), Python Injectors|Native (`apt`), Python Venv|
|**esewa-kafka-ai**|EC2|Zookeeper, Kafka, Debezium, AI Script|Docker Compose|
|**esewa-ch-node1**|`172.31.24.246`|ClickHouse Server, ClickHouse Client|Native (`apt`)|
|**esewa-ch-node2**|`172.31.13.226`|ClickHouse Server, ClickHouse Client|Native (`apt`)|
|**esewa-grafana**|EC2|Grafana UI|Docker|

---

## 3. Database Schema & Data Generation (esewa-mysql)

### 3.1. MySQL Database Setup

The operational database handles incoming core transactions.

- **Database Name:** `esewa_db`
    
- **Table Name:** `wallet_txns`
    

**Schema Initialization SQL:**

SQL

```
USE esewa_db;
CREATE TABLE wallet_txns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type VARCHAR(20),
    amount DECIMAL(15, 2),
    nameOrig VARCHAR(50),
    nameDest VARCHAR(50),
    isFraud TINYINT(1) DEFAULT 0
);
```

### 3.2. High-Throughput Stress Test Script

Generates 10,000 transactions instantly to benchmark ingestion and CDC latency.

- **File Path:** `/home/ubuntu/esewa-fraud-poc/source/stress_test.py`
    
- **Execution:** `sudo python3 stress_test.py`
    

**Code Implementation:**

Python

```
import mysql.connector
import random
from faker import Faker
import time

fake = Faker()

# SRE Socket Hack: Bypassing TCP for faster local ingestion
db = mysql.connector.connect(
  unix_socket="/var/run/mysqld/mysqld.sock",
  user="root",
  password="",
  database="esewa_db"
)
cursor = db.cursor()

print("Starting eSewa SRE Stress Test: Injecting 10,000 Transactions...")
start_time = time.time()
insert_query = "INSERT INTO wallet_txns (type, amount, nameOrig, nameDest, isFraud) VALUES (%s, %s, %s, %s, %s)"

for i in range(10):
    batch_data = []
    for _ in range(1000):
        txn_type = random.choice(['CASH_IN', 'CASH_OUT', 'TRANSFER', 'PAYMENT'])
        amount = round(random.uniform(10.0, 100000.0), 2)
        nameOrig = fake.bothify(text='C#########')
        nameDest = fake.bothify(text='M#########')
        batch_data.append((txn_type, amount, nameOrig, nameDest, 0))
    
    cursor.executemany(insert_query, batch_data)
    db.commit()

end_time = time.time()
print(f"Stress Test Complete! 10,000 records inserted in {round(end_time - start_time, 2)} seconds.")
```

---

## 4. Change Data Capture & Streaming (esewa-kafka-ai)

### 4.1. Docker Compose Configuration (Advanced KRaft Mode)

To ensure maximum performance and low latency, the streaming ecosystem is deployed using Docker with `network_mode: host`. Apache Kafka is configured strictly in **KRaft mode (Zookeeper-less)** with bilingual listeners to handle both internal microservices and external cluster traffic securely.

- **File Path:** `/home/ubuntu/esewa-fraud-poc/kafka/docker-compose.yml`
    
**Actual Configuration Snippet:**

YAML

```
services:
  kafka:
    image: apache/kafka:3.7.0
    container_name: esewa-kafka
    network_mode: host
    environment:
      # KRaft Specific Settings (No Zookeeper)
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@localhost:29093
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER

      # Networking - Bilingual Listeners for AWS VPC
      KAFKA_LISTENERS: INTERNAL://0.0.0.0:29092,CONTROLLER://0.0.0.0:29093,EXTERNAL://0.0.0.0:9092
      KAFKA_ADVERTISED_LISTENERS: INTERNAL://localhost:29092,EXTERNAL://172.31.21.213:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL

      # Cluster Metadata
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0

  debezium:
    image: quay.io/debezium/connect:2.4
    container_name: esewa-debezium
    network_mode: host
    environment:
      - BOOTSTRAP_SERVERS=localhost:29092
      - GROUP_ID=1
      - CONFIG_STORAGE_TOPIC=esewa_connect_configs
      - OFFSET_STORAGE_TOPIC=esewa_connect_offsets
      - STATUS_STORAGE_TOPIC=esewa_connect_statuses
      - CONFIG_STORAGE_REPLICATION_FACTOR=1
      - OFFSET_STORAGE_REPLICATION_FACTOR=1
      - STATUS_STORAGE_REPLICATION_FACTOR=1
      - KEY_CONVERTER=org.apache.kafka.connect.json.JsonConverter
      - VALUE_CONVERTER=org.apache.kafka.connect.json.JsonConverter
    depends_on:
      - kafka

  grafana:
    image: grafana/grafana:latest
    container_name: esewa-grafana
    network_mode: host
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./grafana_storage:/var/lib/grafana
      
  clickhouse:
    image: clickhouse/clickhouse-server:latest
    container_name: esewa-clickhouse
    network_mode: host
    ulimits:
      nofile:
        soft: 262144
        hard: 262144
```
---

## 5. Distributed Data Warehouse (esewa-ch-node1 & esewa-ch-node2)

### 5.1. Cluster Networking Configuration

Both ClickHouse nodes must be introduced to each other to form a unified cluster capable of distributed querying.

- **File Path (On Both Nodes):** `/etc/clickhouse-server/config.d/esewa_cluster.xml`
    
- **Restart Command:** `sudo systemctl restart clickhouse-server`
    

**XML Configuration:**

XML

```
<clickhouse>
    <remote_servers>
        <esewa_cluster>
            <shard>
                <replica>
                    <host>172.31.24.246</host>
                    <port>9000</port>
                </replica>
            </shard>
            <shard>
                <replica>
                    <host>172.31.13.226</host>
                    <port>9000</port>
                </replica>
            </shard>
        </esewa_cluster>
    </remote_servers>
</clickhouse>
```

### 5.2. ClickHouse Table Architecture

To prevent schema desync, the Distributed Table acts as a global router, pointing to the underlying Local Tables on each shard.

**Executed via ClickHouse-Client on Both Nodes:**

SQL

```
-- 1. Create the Local Table (Physical Storage)
CREATE TABLE esewa_db.wallet_txns_local (
    id UInt32,
    type String,
    amount Float64,
    nameOrig String,
    nameDest String,
    isFraud UInt8
) ENGINE = MergeTree()
ORDER BY id;

-- 2. Create the Distributed Table (Global View)
CREATE TABLE esewa_db.wallet_txns_dist AS esewa_db.wallet_txns_local 
ENGINE = Distributed('esewa_cluster', esewa_db, wallet_txns_local, rand());
```

---

## 6. Observability & Visualization (Grafana)

### 6.1. Data Source Configuration

The Grafana ClickHouse plugin (`grafana-clickhouse-datasource`) is utilized to bridge the dashboard to the data warehouse.

- **Server Address:** `172.31.24.246`
    
- **Server Port:** `8123`
    
- **Protocol:** `HTTP`
    
- **Database Name:** `esewa_db`
    

### 6.2. Dashboard Panels & Queries

The Enterprise Command Center consists of three primary real-time panels configured to refresh every 5 seconds.

**Panel 1: Total System Transactions (Stat Panel)**

- _Purpose:_ Monitors CDC pipeline health and total throughput.
    
- _Query:_
    

SQL

```
SELECT count(*) FROM esewa_db.wallet_txns_dist;
```

**Panel 2: Fraud Detected (Stat Panel)**

- _Purpose:_ AI Risk indicator based on defined analytical parameters.
    
- _Query:_
    

SQL

```
SELECT count(*) FROM esewa_db.wallet_txns_dist WHERE amount > 50000;
```

**Panel 3: Live Risk Alert Feed (Table Panel)**

- _Purpose:_ Actionable intelligence feed for SecOps.
    
- _Query:_
    

SQL

```
SELECT 
    id AS Txn_ID, 
    type AS Txn_Type, 
    amount AS Amount_Rs, 
    nameOrig AS Sender 
FROM esewa_db.wallet_txns_dist 
WHERE amount > 50000 
ORDER BY id DESC 
LIMIT 10;
```# eSewa-Fraud-PoC
