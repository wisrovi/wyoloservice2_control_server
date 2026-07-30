#!/usr/bin/env python3
"""Monitor Training Script.

This script queries the NeuralForge AI cluster API to retrieve active running tasks
and identifies which Celery worker (invoker) is executing them.
It then prints the exact commands necessary to check Docker logs on the remote nodes.
"""

import urllib.request
import json
import re
import sys

API_URL = "http://192.168.10.252:23442"

def fetch_json(endpoint: str):
    """Fetches JSON data from the specified API endpoint."""
    url = f"{API_URL}/{endpoint}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching data from {url}: {e}", file=sys.stderr)
        return None

def extract_ip_from_worker(worker_name: str, workers_data: dict) -> str:
    """Helper to extract IP address from celery worker name."""
    if not worker_name:
        return "Unknown"
    
    # Try finding in workers dict
    if workers_data and worker_name in workers_data:
        info = workers_data[worker_name]
        if isinstance(info, list) and len(info) > 0:
            return info[0]

    # Fallback to parsing the name, e.g., celery@wyolo_invoker_192.168.1.52
    match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', worker_name)
    if match:
        return match.group(1)
        
    return "Unknown"

def main():
    print("=" * 80)
    print("   NEURALFORGE AI - DISTRIBUTED TRAINING MONITOR")
    print("=" * 80)
    print(f"Connecting to cluster API at: {API_URL}...\n")

    # Fetch status
    workers_res = fetch_json("workers")
    tasks_res = fetch_json("tasks")

    if not workers_res or not tasks_res:
        print("Could not retrieve cluster information. Please check if the API is online.")
        sys.exit(1)

    workers_dict = workers_res.get("workers", {})
    running_tasks = tasks_res.get("running", [])

    if not running_tasks:
        print("No active training tasks are currently running in the cluster.")
        print("=" * 80)
        sys.exit(0)

    print(f"Found {len(running_tasks)} active task(s) running:\n")

    for i, task in enumerate(running_tasks, 1):
        task_id = task.get("id")
        worker_name = task.get("worker")
        task_name = task.get("name")
        args_str = task.get("args", "")

        # Determine worker IP
        invoker_ip = extract_ip_from_worker(worker_name, workers_dict)

        print(f"[{i}] TASK ID: {task_id}")
        print(f"    Name:       {task_name}")
        print(f"    Worker:     {worker_name} (IP: {invoker_ip})")
        
        # Try to parse arguments to print model/dataset (handles truncated string gracefully)
        model = "N/A"
        dataset = "N/A"
        try:
            model_match = re.search(r"'model':\s*'([^']+)'", args_str)
            if model_match:
                model = model_match.group(1)
            
            data_match = re.search(r"'data':\s*'([^']+)'", args_str)
            if data_match:
                dataset = data_match.group(1)
        except Exception:
            pass

        print(f"    Model:      {model}")
        print(f"    Dataset:    {dataset}")
        
        if "train_on_gpu" in task_name:
            print("\n    --> HOW TO CHECK LOGS FOR THIS TRAINING:")
            if invoker_ip != "Unknown" and invoker_ip != "managers":
                # Command to check docker logs
                executor_name = f"wyolo_executor_{invoker_ip}"
                print(f"        1. Docker logs (real-time stream):")
                print(f"           ssh -t wyolo@{invoker_ip} \"docker logs -f {executor_name}\"")
                print(f"        2. Log file (persistent log file on host):")
                print(f"           ssh -t wyolo@{invoker_ip} \"tail -f /home/wyolo/train_service_results/logs_{executor_name}.txt\"")
            else:
                print("        Could not resolve invoker IP. Check the container logs directly on the corresponding host node.")
        else:
            print("\n    --> TASK INFO:")
            print("        This is a management/orchestration task running on the cluster manager node.")
        print("-" * 80)

if __name__ == "__main__":
    main()
