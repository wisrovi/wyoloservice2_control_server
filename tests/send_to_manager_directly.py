REDIS_HOST = "192.168.10.252"


import yaml
import os
import sys
from celery import Celery

# Ensure the parent directory is in the path so we can import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REDIS_PORT = "23437"
REDIS_HOST = os.getenv("CONTROL_HOST", REDIS_HOST)
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"


celery_app = Celery("neuralforge_launcher", broker=REDIS_URL, backend=REDIS_URL)


def send_test_study():
    # Use relative path based on this script's location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_path = os.path.join(base_dir, "test_to_send_manager.yaml")

    if not os.path.exists(yaml_path):
        print(f"[-] Error: {yaml_path} not found.")
        return

    print(f"[*] Reading configuration from: {yaml_path}")
    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)

    study_name = config.get("sweeper", {}).get("study_name", "unknown")
    priority = config.get("sweeper", {}).get("priority", "low (default)")

    print(f"[*] Sending study request for: {study_name}")
    print(f"[*] Target Priority: {priority}")
    print(f"[*] Redis Broker: {celery_app.conf.broker_url}")

    try:
        # Send the task to the managers queue
        result = celery_app.send_task("tasks.manage_study", args=[config], queue="managers")

        print("\n" + "=" * 40)
        print(f"✅ Success! Task ID: {result.id}")
        print(f"[*] Task sent to 'managers' queue.")
        print(f"[*] MONITOR: docker logs wyolo_manager -f")
        print("=" * 40)
    except Exception as e:
        print(f"[-] Error sending task: {e}")
        print("[!] Ensure CONTROL_HOST or REDIS_URL is set in your environment.")


if __name__ == "__main__":
    send_test_study()
