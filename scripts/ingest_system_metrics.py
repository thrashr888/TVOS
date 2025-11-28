import time
import zmq
import uuid
import json
import sys
from tvos.protos.events_pb2 import EventPayload
from tvos.config import Config

# Try to import psutil, warn if missing
try:
    import psutil
except ImportError:
    print("Error: 'psutil' library is required. Install with: pip install psutil")
    sys.exit(1)


def ingest_system_metrics(interval=5):
    context = zmq.Context()
    sender = context.socket(zmq.PUSH)
    sender.connect(f"tcp://{Config.ZMQ_HOST}:{Config.ZMQ_PULL_PORT}")

    print(f"Starting system metrics ingestion (interval: {interval}s)...")

    try:
        while True:
            event = EventPayload()
            event.event_id = str(uuid.uuid4())
            event.timestamp_ms = int(time.time() * 1000)
            event.source = "system_metrics"

            # Collect metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Top processes by CPU
            top_procs = []
            for proc in sorted(
                psutil.process_iter(["pid", "name", "cpu_percent"]),
                key=lambda p: p.info["cpu_percent"],
                reverse=True,
            )[:3]:
                top_procs.append(f"{proc.info['name']}({proc.info['cpu_percent']}%)")

            event.text_payload = f"System Load: CPU {cpu_percent}% | Mem {memory.percent}% | Top: {', '.join(top_procs)}"

            event.metrics["cpu_percent"] = cpu_percent
            event.metrics["memory_percent"] = memory.percent
            event.metrics["disk_percent"] = disk.percent
            event.metrics["bytes_sent"] = psutil.net_io_counters().bytes_sent
            event.metrics["bytes_recv"] = psutil.net_io_counters().bytes_recv

            event.metadata["host"] = "localhost"
            event.metadata["top_processes"] = json.dumps(top_procs)

            sender.send(event.SerializeToString())
            print(f"Sent metrics: CPU {cpu_percent}%")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopping metrics ingestion...")


if __name__ == "__main__":
    ingest_system_metrics()
