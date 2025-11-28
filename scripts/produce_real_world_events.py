import zmq
import time
import uuid
import random
from tvos.protos.events_pb2 import EventPayload
from tvos.config import Config

def produce():
    context = zmq.Context()
    sender = context.socket(zmq.PUSH)
    sender.connect(f"tcp://localhost:{Config.ZMQ_PULL_PORT}")
    
    print("Starting real-world event simulation...")
    
    sources = ["auth_service", "payment_gateway", "firewall", "load_balancer", "app_server"]
    
    templates = {
        "auth_service": [
            "User {user} logged in successfully from {ip}",
            "Failed login attempt for user {user} from {ip}",
            "Password reset requested for {user}",
            "Session expired for {user}"
        ],
        "payment_gateway": [
            "Payment processed for order {order} amount ${amount}",
            "Payment declined for order {order}: Insufficient funds",
            "Refund processed for order {order}",
            "Gateway timeout connecting to provider"
        ],
        "firewall": [
            "Blocked suspicious traffic from {ip} on port 80",
            "Allowed connection from {ip} to port 443",
            "DDoS attack detected from subnet {subnet}",
            "Port scan detected from {ip}"
        ],
        "load_balancer": [
            "Backend server {server} is healthy",
            "Backend server {server} is unresponsive",
            "High latency detected on route /api/v1/search",
            "Redirecting traffic to secondary region"
        ],
        "app_server": [
            "Database connection timeout after 5000ms",
            "Cache miss for key {key}",
            "Processed background job {job} in {ms}ms",
            "Out of memory error in worker process"
        ]
    }
    
    users = ["alice", "bob", "charlie", "admin", "support"]
    ips = ["192.168.1.1", "10.0.0.5", "45.33.22.11", "203.0.113.42"]
    subnets = ["45.33.0.0/16", "203.0.113.0/24"]
    
    try:
        while True:
            source = random.choice(sources)
            template = random.choice(templates[source])
            
            # Generate variables
            text = template.format(
                user=random.choice(users),
                ip=random.choice(ips),
                order=f"ORD-{random.randint(1000, 9999)}",
                amount=random.randint(10, 500),
                subnet=random.choice(subnets),
                server=f"srv-{random.randint(1, 5)}",
                key=f"cache_key_{random.randint(1, 100)}",
                job=f"job_{random.randint(1, 50)}",
                ms=random.randint(10, 500)
            )
            
            event = EventPayload()
            event.event_id = str(uuid.uuid4())
            event.timestamp_ms = int(time.time() * 1000)
            event.source = source
            event.text_payload = text
            
            # Add some metrics
            event.metrics["latency"] = random.uniform(10, 200)
            event.metrics["cpu"] = random.uniform(0.1, 0.9)
            if "timeout" in text or "error" in text or "failed" in text or "declined" in text:
                event.metrics["error_count"] = 1.0
                event.metadata["severity"] = "error"
            else:
                event.metadata["severity"] = "info"
                
            event.metadata["env"] = "production"
            
            sender.send(event.SerializeToString())
            print(f"[{source}] {text}")
            
            # Variable sleep to simulate bursts (faster)
            time.sleep(random.uniform(0.05, 0.3))
            
    except KeyboardInterrupt:
        print("Stopping producer...")

if __name__ == "__main__":
    produce()

