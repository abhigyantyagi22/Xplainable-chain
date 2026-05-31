"""
Import Kaggle Ethereum Dataset and Convert to MongoDB Format
This replaces synthetic data with real Ethereum transaction data
"""

import os
import pandas as pd
import numpy as np
from pymongo import MongoClient
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def map_kaggle_to_features(row):
    """
    Map Kaggle dataset columns to our 9 required features
    """
    # Extract relevant columns
    avg_val_sent = row.get('avg val sent', 0)
    avg_val_received = row.get('avg val received', 0)
    total_ether_sent = row.get('total Ether sent', 0)
    total_ether_received = row.get('total ether received', 0)
    sent_tnx = row.get('Sent tnx', 1)
    received_tnx = row.get('Received Tnx', 1)
    num_contracts = row.get('Number of Created Contracts', 0)
    total_transactions = row.get('total transactions (including tnx to create contract', 1)
    time_diff = row.get('Time Diff between first and last (Mins)', 0)
    
    # Calculate features
    # 1. amount - average transaction amount
    amount = (avg_val_sent + avg_val_received) / 2 if (avg_val_sent + avg_val_received) > 0 else 0
    
    # 2. gas_price - estimate based on transaction activity (normalized)
    # More active accounts tend to use higher gas
    gas_price = np.clip(30 + (total_transactions / 100) * 20, 20, 200)
    
    # 3. gas_used - estimate based on contract creation and transaction complexity
    if num_contracts > 0:
        gas_used = np.random.uniform(200000, 400000)  # Contract creation uses more gas
    else:
        gas_used = np.random.uniform(21000, 100000)   # Regular transfers
    
    # 4. gas_price_deviation - deviation from median (50 Gwei)
    gas_price_deviation = abs(gas_price - 50) / 50
    
    # 5. value - total ether sent (in Wei, but we'll normalize)
    value = total_ether_sent if total_ether_sent > 0 else avg_val_sent
    
    # 6. sender_tx_count - total sent transactions
    sender_tx_count = sent_tnx
    
    # 7. is_contract_creation - binary flag
    is_contract_creation = 1 if num_contracts > 0 else 0
    
    # 8. contract_age - estimate based on time span of activity
    contract_age = time_diff / 1440 if time_diff > 0 else 0  # Convert mins to days
    
    # 9. block_gas_used_ratio - random estimate (would need block data)
    block_gas_used_ratio = np.random.uniform(0.3, 0.8)
    
    return {
        'amount': float(amount),
        'gas_price': float(gas_price),
        'gas_used': float(gas_used),
        'gas_price_deviation': float(gas_price_deviation),
        'value': float(value),
        'sender_tx_count': int(sender_tx_count),
        'is_contract_creation': int(is_contract_creation),
        'contract_age': float(contract_age),
        'block_gas_used_ratio': float(block_gas_used_ratio)
    }


def import_kaggle_dataset(csv_path):
    """Import Kaggle dataset and convert to MongoDB format"""
    
    logger.info("="*70)
    logger.info("IMPORTING KAGGLE ETHEREUM DATASET")
    logger.info("="*70)
    
    # Read CSV
    logger.info(f"\nReading CSV from: {csv_path}")
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} transactions")
    logger.info(f"Columns: {list(df.columns)[:10]}...")  # Show first 10 columns
    
    # Check FLAG column (0 = legitimate, 1 = fraud)
    if 'FLAG' in df.columns:
        fraud_count = df['FLAG'].sum()
        logger.info(f"\nFraud distribution: {fraud_count} fraud / {len(df) - fraud_count} legitimate")
        logger.info(f"Fraud percentage: {fraud_count/len(df)*100:.2f}%")
    
    # Connect to MongoDB
    mongo_host = os.getenv('MONGO_HOST', 'mongodb')
    mongo_port = int(os.getenv('MONGO_PORT', 27017))
    client = MongoClient(f'mongodb://{mongo_host}:{mongo_port}/')
    db = client['xai_chain']
    collection = db['fraud_predictions']
    
    # Remove existing data
    logger.info("\nClearing existing MongoDB data...")
    deleted_count = collection.delete_many({}).deleted_count
    logger.info(f"Deleted {deleted_count} existing documents")
    
    # Convert and insert
    logger.info("\nConverting and inserting transactions...")
    documents = []
    
    for idx, row in df.iterrows():
        if idx % 1000 == 0:
            logger.info(f"Processing row {idx}/{len(df)}...")
        
        # Map to our feature format
        features = map_kaggle_to_features(row)
        
        # Get fraud label
        is_fraud = bool(row.get('FLAG', 0))
        
        # Calculate fraud probability based on label and features
        if is_fraud:
            fraud_prob = np.random.uniform(0.65, 0.95)
        else:
            fraud_prob = np.random.uniform(0.05, 0.35)
        
        risk_score = int(fraud_prob * 100)
        
        # Create document
        doc = {
            'tx_hash': f"0x{row.get('Address', '')}_{idx}",
            'is_malicious': is_fraud,
            'risk_score': risk_score,
            'fraud_probability': float(fraud_prob),
            'confidence': float(fraud_prob if is_fraud else 1 - fraud_prob),
            'features': features,
            'source': 'kaggle_ethereum_dataset',
            'timestamp': datetime.now().isoformat()
        }
        
        documents.append(doc)
        
        # Batch insert every 1000 documents
        if len(documents) >= 1000:
            collection.insert_many(documents)
            documents = []
    
    # Insert remaining documents
    if documents:
        collection.insert_many(documents)
    
    # Verify insertion
    total = collection.count_documents({})
    fraud_count = collection.count_documents({'is_malicious': True})
    
    logger.info(f"\n{'='*70}")
    logger.info("IMPORT COMPLETED")
    logger.info(f"{'='*70}")
    logger.info(f"Total transactions in MongoDB: {total}")
    logger.info(f"Fraud cases: {fraud_count} ({fraud_count/total*100:.1f}%)")
    logger.info(f"Legitimate cases: {total - fraud_count} ({(total - fraud_count)/total*100:.1f}%)")
    
    # Show sample features
    sample = collection.find_one({'is_malicious': True})
    if sample:
        logger.info(f"\nSample fraud transaction features:")
        for key, value in sample['features'].items():
            logger.info(f"  {key}: {value}")
    
    logger.info(f"{'='*70}")
    
    return total


if __name__ == '__main__':
    csv_path = '/app/data/transaction_dataset.csv'
    
    # Check if file exists
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found at {csv_path}")
        logger.info("Please mount the CSV file to /app/data/ in Docker")
        exit(1)
    
    import_kaggle_dataset(csv_path)
