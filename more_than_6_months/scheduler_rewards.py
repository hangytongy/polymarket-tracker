import subprocess
import time
import os

LOCK_FILE = "/tmp/rewards_running.lock"

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
            print("Running rewards.py...")
            subprocess.run(
                ["venv/bin/python3", "mm.py"],
                cwd="/root/polymarket-tracker/more_than_6_months",
                check=False
            )
        finally:
            remove_lock()
    else:
        print("Skipping run — previous one still active.")
    
    time.sleep(60*3)   # run every 30 seconds
