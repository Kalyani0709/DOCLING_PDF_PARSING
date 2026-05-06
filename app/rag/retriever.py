from opensearchpy import OpenSearch
from app.rag.config import *
from app.rag.embedder import Embedder
from sentence_transformers import CrossEncoder
import re

client = OpenSearch(
    hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}]
)

embedder = Embedder(EMBEDDING_MODEL)
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def clean_preview(text, max_len=300):
    text = re.sub(r"\s+", " ", text)
    return text[:max_len]


# ✅ FIXED FILTER
def is_low_value_chunk(text):
    text = text.strip()

    # too short = low info
    if len(text.split()) < 20:
        return True

    # only separators
    if set(text) <= {"-", "|", " "}:
        return True

    return False


def rerank(query, docs, top_k=5, debug=False):
    if not docs:
        return docs

    pairs = [
        (
            query,
            f"""
            Section: {doc['metadata'].get('section', '')}
            Page: {doc['metadata'].get('page', '')}
            Content: {doc['text'][:500]}
            """
        )
        for doc in docs
    ]

    scores = reranker.predict(pairs)

    for i, doc in enumerate(docs):
        doc["rerank_score"] = float(scores[i])

    docs = sorted(docs, key=lambda x: x["rerank_score"], reverse=True)

    if debug:
        print("\n🔁 RERANK RESULTS:")
        for i, d in enumerate(docs[:10]):
            print(f"[{i}] RERANK_SCORE={d['rerank_score']:.4f} | SECTION={d['metadata'].get('section')}")
            print(clean_preview(d["text"]))
            print("-" * 80)

    return docs[:top_k]


# ✅ NEW: combine scores
def normalize_scores(docs):
    for doc in docs:
        doc["final_score"] = (
            0.7 * doc.get("rerank_score", 0) +
            0.3 * doc.get("score", 0)
        )
    return sorted(docs, key=lambda x: x["final_score"], reverse=True)


def retrieve(query, top_k=5, fetch_k=50, debug=True):

    print("\n" + "=" * 80)
    print(f"🔍 QUERY: {query}")
    print("=" * 80)

    query_vector = embedder.encode([query])[0]

    search_body = {
        "size": fetch_k,
        "query": {
            "bool": {
                "should": [
                    {
                        "match_phrase": {
                            "text": {
                                "query": query,
                                "boost": 4
                            }
                        }
                    },
                    {
                        "match_phrase": {
                            "section": {
                                "query": query,
                                "boost": 3
                            }
                        }
                    },
                    {
                        "match": {
                            "text": {
                                "query": query,
                                "boost": 2
                            }
                        }
                    },
                    {
                        "knn": {
                            "embedding": {
                                "vector": query_vector,
                                "k": fetch_k
                            }
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
    }

    response = client.search(index=INDEX_NAME, body=search_body)

    docs = []
    for hit in response["hits"]["hits"]:
        docs.append({
            "text": hit["_source"]["text"],
            "score": hit["_score"],
            "metadata": hit["_source"]
        })

    if debug:
        print("\n📦 RAW RETRIEVAL RESULTS:")
        for i, d in enumerate(docs[:10]):
            print(f"[{i}] SCORE={d['score']:.4f} | SECTION={d['metadata'].get('section')}")
            print(clean_preview(d["text"]))
            print("-" * 80)

    # ✅ SAFE FILTERING
    docs = [d for d in docs if not is_low_value_chunk(d["text"])]

    if debug:
        print("\n🧹 AFTER FILTERING:")
        for i, d in enumerate(docs[:10]):
            print(f"[{i}] SCORE={d['score']:.4f} | SECTION={d['metadata'].get('section')}")
            print(clean_preview(d["text"]))
            print("-" * 80)

    # rerank on larger pool
    reranked = rerank(query, docs, top_k=fetch_k, debug=debug)

    # final scoring
    final_docs = normalize_scores(reranked)[:top_k]

    print("\n✅ FINAL TOP RESULTS:")
    for i, d in enumerate(final_docs):
        print(f"[{i}] FINAL SCORE={d['final_score']:.4f} | SECTION={d['metadata'].get('section')}")
        print(clean_preview(d["text"]))
        print("=" * 80)

    return final_docs