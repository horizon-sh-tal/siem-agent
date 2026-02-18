#!/usr/bin/env python3
"""
FTP Activity Monitor - Tracks file changes and sends to Kafka
Monitors: uploads, downloads, modifications, deletions
"""

import os
import time
import hashlib
import json
from kafka import KafkaProducer
from kafka.errors import KafkaError
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
FTP_DATA_DIR = '/ftp-data'
KAFKA_BROKER = '192.168.27.211:9092'
KAFKA_TOPIC = 'ftp-activity-logs'
SCAN_INTERVAL = 1800  # 30 minutes (1800 seconds)

def create_kafka_producer():
    """Create Kafka producer with retry logic"""
    max_retries = 5
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                max_block_ms=5000,
                request_timeout_ms=10000
            )
            logger.info(f"Connected to Kafka broker at {KAFKA_BROKER}")
            return producer
        except KafkaError as e:
            logger.warning(f"Kafka connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("Failed to connect to Kafka after all retries")
                raise

def hash_file(filepath):
    """Calculate SHA256 hash of a file"""
    try:
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.error(f"Error hashing file {filepath}: {e}")
        return None

def get_file_metadata(filepath):
    """Get file metadata including size, modification time"""
    try:
        stat = os.stat(filepath)
        return {
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'accessed': datetime.fromtimestamp(stat.st_atime).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting metadata for {filepath}: {e}")
        return None

def scan_directory():
    """Scan FTP directory and return file information"""
    file_info = {}
    
    if not os.path.exists(FTP_DATA_DIR):
        logger.error(f"FTP data directory not found: {FTP_DATA_DIR}")
        return file_info
    
    for root, dirs, files in os.walk(FTP_DATA_DIR):
        # Determine which FTP account this directory belongs to
        relative_path = os.path.relpath(root, FTP_DATA_DIR)
        account = relative_path.split(os.sep)[0] if relative_path != '.' else 'unknown'
        
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                file_hash = hash_file(fpath)
                metadata = get_file_metadata(fpath)
                
                if file_hash and metadata:
                    file_info[fpath] = {
                        'hash': file_hash,
                        'account': account,
                        'filename': fname,
                        'path': fpath,
                        'relative_path': os.path.relpath(fpath, FTP_DATA_DIR),
                        **metadata
                    }
            except Exception as e:
                logger.error(f"Error processing file {fpath}: {e}")
                continue
    
    return file_info

def detect_changes(previous, current):
    """Detect file changes between two scans"""
    changes = {
        'new_files': [],
        'modified_files': [],
        'deleted_files': []
    }
    
    # Find new and modified files
    for fpath, info in current.items():
        if fpath not in previous:
            changes['new_files'].append(info)
            logger.info(f"New file detected: {info['relative_path']} (account: {info['account']})")
        elif previous[fpath]['hash'] != info['hash']:
            changes['modified_files'].append({
                **info,
                'previous_hash': previous[fpath]['hash'],
                'previous_size': previous[fpath]['size']
            })
            logger.info(f"Modified file detected: {info['relative_path']} (account: {info['account']})")
    
    # Find deleted files
    for fpath, info in previous.items():
        if fpath not in current:
            changes['deleted_files'].append(info)
            logger.info(f"Deleted file detected: {info['relative_path']} (account: {info['account']})")
    
    return changes

def send_to_kafka(producer, changes, scan_time):
    """Send change events to Kafka"""
    if not any(changes.values()):
        logger.info("No changes detected in this scan cycle")
        return
    
    event = {
        'timestamp': scan_time.isoformat(),
        'event_type': 'ftp_activity_scan',
        'machine_id': 'ftp-server',
        'changes': changes,
        'summary': {
            'new_files': len(changes['new_files']),
            'modified_files': len(changes['modified_files']),
            'deleted_files': len(changes['deleted_files'])
        }
    }
    
    try:
        future = producer.send(KAFKA_TOPIC, event)
        future.get(timeout=10)  # Block until message is sent
        logger.info(f"Sent activity log to Kafka: {event['summary']}")
    except KafkaError as e:
        logger.error(f"Failed to send to Kafka: {e}")

def main():
    """Main monitoring loop"""
    logger.info("=" * 60)
    logger.info("FTP Activity Monitor Starting")
    logger.info(f"Monitoring directory: {FTP_DATA_DIR}")
    logger.info(f"Kafka broker: {KAFKA_BROKER}")
    logger.info(f"Kafka topic: {KAFKA_TOPIC}")
    logger.info(f"Scan interval: {SCAN_INTERVAL} seconds ({SCAN_INTERVAL/60} minutes)")
    logger.info("=" * 60)
    
    # Create Kafka producer
    producer = create_kafka_producer()
    
    # Initial scan
    logger.info("Performing initial scan...")
    previous_scan = scan_directory()
    logger.info(f"Initial scan complete: {len(previous_scan)} files found")
    
    # Monitoring loop
    try:
        while True:
            logger.info(f"Waiting {SCAN_INTERVAL} seconds until next scan...")
            time.sleep(SCAN_INTERVAL)
            
            scan_time = datetime.now()
            logger.info(f"Starting scan at {scan_time.isoformat()}")
            
            current_scan = scan_directory()
            logger.info(f"Scan complete: {len(current_scan)} files found")
            
            changes = detect_changes(previous_scan, current_scan)
            send_to_kafka(producer, changes, scan_time)
            
            previous_scan = current_scan
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring error: {e}", exc_info=True)
    finally:
        if producer:
            producer.flush()
            producer.close()
        logger.info("FTP Activity Monitor stopped")

if __name__ == '__main__':
    main()
