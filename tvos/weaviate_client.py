import weaviate
import weaviate.classes.config as wvc
import weaviate.classes.query as wvq
from tvos.config import Config
import time


class WeaviateClient:
    def __init__(self):
        self.client = weaviate.connect_to_local(
            host=Config.WEAVIATE_URL.split("://")[1].split(":")[0],
            port=int(Config.WEAVIATE_URL.split(":")[-1]),
        )

    def init_schema(self):
        if not self.client.collections.exists("EventEmbedding"):
            self.client.collections.create(
                name="EventEmbedding",
                vectorizer_config=wvc.Configure.Vectorizer.none(),
                properties=[
                    wvc.Property(name="event_id", data_type=wvc.DataType.TEXT),
                    wvc.Property(name="timestamp", data_type=wvc.DataType.DATE),
                    wvc.Property(name="source", data_type=wvc.DataType.TEXT),
                ],
            )
            print("Created Weaviate schema for EventEmbedding")

    def insert_embedding(
        self, event_id: str, vector: list, timestamp_ms: int, source: str
    ):
        collection = self.client.collections.get("EventEmbedding")
        # Weaviate expects RFC3339 date string or datetime object.
        # For simplicity in this wrapper, we might need to convert ms to datetime if strict typing is enforced,
        # but the RFC said "date" type. Let's use ISO string.
        from datetime import datetime, timezone

        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

        collection.data.insert(
            properties={"event_id": event_id, "timestamp": dt, "source": source},
            vector=vector,
        )

    def search_similar(self, vector: list, limit: int = 10):
        collection = self.client.collections.get("EventEmbedding")
        response = collection.query.near_vector(
            near_vector=vector,
            limit=limit,
            return_metadata=wvq.MetadataQuery(distance=True),
        )
        return response.objects

    def close(self):
        self.client.close()


if __name__ == "__main__":
    client = WeaviateClient()
    client.init_schema()
    client.close()
