CREATE DATABASE IF NOT EXISTS esewa_db;
USE esewa_db;

-- Debezium ko lagi dedicated user banaune (Zero-Trust Security)
CREATE USER IF NOT EXISTS 'debezium_user'@'%' IDENTIFIED WITH mysql_native_password BY 'eSewaStrongPass123!';
GRANT SELECT, RELOAD, SHOW DATABASES, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'debezium_user'@'%';
FLUSH PRIVILEGES;

CREATE TABLE live_wallet_txns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    step INT,
    type VARCHAR(20),
    amount DECIMAL(15,2),
    nameOrig VARCHAR(50),
    oldbalanceOrg DECIMAL(15,2),
    newbalanceOrig DECIMAL(15,2),
    nameDest VARCHAR(50),
    isFraud INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);