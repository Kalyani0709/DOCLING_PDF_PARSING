from opensearchpy import OpenSearch
from app.rag.config import OPENSEARCH_HOST, OPENSEARCH_PORT, INDEX_NAME

def create_index():
    client = OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        http_compress=True
    )

    mapping = {
        "settings": {
            "index": {
                "knn": True
            }
        },
        "mappings": {
            "properties": {
                "text": {"type": "text"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 384
                },
                "page": {"type": "integer"},
                "section": {"type": "keyword"},
                "year": {"type": "keyword"},
                "make": {"type": "keyword"},
                "model": {"type": "keyword"},
                "pdf_url": {"type": "keyword"}
            }
        }
    }

    if client.indices.exists(index=INDEX_NAME):
        print("Index already exists")
    else:
        client.indices.create(index=INDEX_NAME, body=mapping)
        print("Index created")

if __name__ == "__main__":
    create_index()