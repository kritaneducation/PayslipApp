import sys
import requests

REMOTE_VERSION_URL = "https://example.com/payslip_app_version.txt"  # Replace with your actual version file URL


def get_remote_version():
    try:
        response = requests.get(REMOTE_VERSION_URL, timeout=5)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print(f"Error checking for updates: {e}")
        return None


def check_for_update(current_version):
    remote_version = get_remote_version()
    if remote_version is None:
        print("Could not check for updates. Exiting for safety.")
        sys.exit(1)
    if remote_version != current_version:
        print(f"A new version ({remote_version}) is available. Please update the application.")
        sys.exit(1)
    else:
        print("Application is up to date.")
