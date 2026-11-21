import os
import uuid
import json
import socket
import subprocess
import requests

from datetime import datetime, timezone
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

CENTRAL_URL = "http://MINIPC_IP:8000/api/v1/events"
PROJECT_PATH = Path(r"D:\Projects\CaiLun")
DEVICE_ID = str(uuid.getnode())

def git_info():
    def run(cmd):
        return subprocess.run(
            cmd,
            cwd=PROJECT_PATH,
            capture_output=True,
            text=True
        ).stdout.strip()

    return {
        "branch": run(["git", "branch", "--show-current"]),
        "commit": run(["git", "rev-parse", "HEAD"])
    }

def send_event(event_type, payload):
    git = git_info()

    event = {
        "protocol": "nexusmind.event",
        "schema_version": "1.0.0",
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),

        "device": {
            "device_id": DEVICE_ID,
            "device_name": socket.gethostname(),
            "device_type": "desktop"
        },

        "project": {
            "project_id": "proj_cailun",
            "project_name": "蔡伦系统",
            "project_path": str(PROJECT_PATH),
            "branch": git["branch"]
        },

        "payload": payload
    }

    try:
        requests.post(
            CENTRAL_URL,
            json=event,
            timeout=5
        ).raise_for_status()
    except requests.RequestException as e:
        print(f"Event delivery failed: {e}")

class GitEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)

        if ".git" in path.parts:
            return

        send_event("file.changed", {
            "file_path": str(path.relative_to(PROJECT_PATH)),
            "change_type": "modified"
        })

if __name__ == "__main__":
    observer = Observer()
    observer.schedule(
        GitEventHandler(),
        str(PROJECT_PATH),
        recursive=True
    )

    observer.start()
    print("NexusMind Agent started.")

    try:
        while True:
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()