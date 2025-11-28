import zmq
import time
import uuid
from tvos.protos.events_pb2 import EventPayload
from tvos.config import Config

def produce():
    context = zmq.Context()
    sender = context.socket(zmq.PUSH)
    sender.connect(f"tcp://localhost:{Config.ZMQ_PULL_PORT}")
    
    for i in range(5):
        event = EventPayload()
        event.event_id = str(uuid.uuid4())
        event.timestamp_ms = int(time.time() * 1000)
        event.source = "test_producer"
        event.text_payload = f"This is test message {i}"
        event.metrics["cpu"] = 0.5 + (i * 0.1)
        event.metadata["env"] = "dev"
        
        sender.send(event.SerializeToString())
        print(f"Sent event {event.event_id}")
        time.sleep(0.1)

if __name__ == "__main__":
    produce()
