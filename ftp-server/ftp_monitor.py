import os
import time
import hashlib
import json
from kafka import KafkaProducer
from datetime import datetime

FTP_DATA_DIR = '/ftp-data'  # Adjust if needed
KAFKA_BROKER = '192.168.27.211:9092'
KAFKA_TOPIC = 'ftp-activity-logs'
SCAN_INTERVAL = 1800  # 30 minutes

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def scan_and_log():
    file_hashes = {}
    for root, dirs, files in os.walk(FTP_DATA_DIR):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                h = hash_file(fpath)
                file_hashes[fpath] = h
            except Exception as e:
                continue
    return file_hashes

def main():
    last_hashes = {}
    while True:
        current_hashes = scan_and_log()
        changed = []
        for f, h in current_hashes.items():
            if f not in last_hashes or last_hashes[f] != h:
                changed.append({'file': f, 'hash': h, 'timestamp': datetime.now().isoformat()})
        if changed:
            producer.send(KAFKA_TOPIC, {'event': 'file_change', 'changes': changed})
        last_hashes = current_hashes
        time.sleep(SCAN_INTERVAL)

if __name__ == '__main__':
    main()
