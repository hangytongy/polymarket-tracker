import subprocess
import time
import os

LOCK_FILE = "/tmp/btc_running.lock"

def is_running():
    return os.path.exists(LOCK_FILE)

def create_lock():
    open(LOCK_FILE, "w").close()

def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

while True:
    if not is_running():
        try:
            create_lock()
            print("Running BTC limit_sell_positions.py...")
            subprocess.run(
                ["venv/bin/python3", "limit_sell_positions.py"],
                cwd="/root/polymarket-tracker/btc_vol_spam",
                check=False
            )
        finally:
            remove_lock()
    else:
        print("Skipping run — previous one still active.")
    
    time.sleep(15)   # run every 30 seconds
