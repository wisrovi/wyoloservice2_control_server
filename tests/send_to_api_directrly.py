import requests
import os

BASE_YAML = "config_train.yaml"
BASE_YAML = "config_train.basic.yaml"


def test_api_send_training():
    # Configuration
    api_url = "http://localhost:23442/train"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_path = os.path.join(base_dir, BASE_YAML)

    if not os.path.exists(yaml_path):
        print(f"[-] Error: {yaml_path} not found.")
        return

    print(f"[*] Target API: {api_url}")
    print(f"[*] Reading config from: {yaml_path}")

    # Prepare the multipart/form-data request
    try:
        with open(yaml_path, "rb") as f:
            files = {
                "config_file": (os.path.basename(yaml_path), f, "application/x-yaml")
            }
            data = {"mode": "public", "priority": "low"}

            print("[*] Sending request...")
            response = requests.post(api_url, files=files, data=data)

        if response.status_code == 200:
            print("\n" + "=" * 40)
            print("✅ Success! API accepted the study.")
            print(f"[*] Response: {response.json()}")
            print("=" * 40)
        else:
            print("\n" + "!" * 40)
            print(f"❌ Error: {response.status_code}")
            print(f"[*] Detail: {response.text}")
            print("!" * 40)

    except Exception as e:
        print(f"[-] Request failed: {e}")


if __name__ == "__main__":
    test_api_send_training()
