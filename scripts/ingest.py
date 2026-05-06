import json
from tqdm import tqdm
from opensearchpy import OpenSearch, helpers

from app.rag.config import (
    OPENSEARCH_HOST,
    OPENSEARCH_PORT,
    INDEX_NAME,
    EMBEDDING_MODEL,
)
from app.rag.embedder import Embedder


# OpenSearch client
client = OpenSearch(
    hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
    http_compress=True,
)

embedder = Embedder(EMBEDDING_MODEL)


def ingest(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} chunks")

    # Generate embeddings
    texts = [d["text"] for d in data]
    embeddings = embedder.encode(texts)

    actions = []

    for i, chunk in enumerate(tqdm(data)):
        doc = {
            "text": chunk["text"],
            "embedding": embeddings[i],
            **chunk["metadata"],
        }

        actions.append({
            "_index": INDEX_NAME,
            "_source": doc
        })

    helpers.bulk(client, actions)

    print("✅ Ingestion complete")


if __name__ == "__main__":
    ingest("data/chunked.json")