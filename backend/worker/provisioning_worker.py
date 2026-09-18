import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.worker.provisioning_worker import run_worker_loop

if __name__ == "__main__":
    run_worker_loop()
