from app.rag.retriever import retrieve

def get_answer(question: str, year: int, brand: str, model: str):
    docs = retrieve(question)

    print("\n\n========== RETRIEVED CONTEXT ==========")
    for i, d in enumerate(docs):
        print(f"\n--- DOC {i} (Page {d['metadata'].get('page')}) ---")
        print(d["text"])
    print("=======================================\n\n")

    context = "\n\n".join([
        f"[Page {d['metadata'].get('page')}] {d['text']}"
        for d in docs
    ])

    prompt = f"""
You are an automotive Owner’s Manual assistant.

You must answer ONLY using the provided context.

RULES:
- Use ONLY the context below.
- Do NOT add information from general automotive knowledge.
- Do NOT mix multiple warning lights or systems.
- If the context does not fully answer the question, say:
  "This information is not available in the provided owner’s manual excerpt."
- Keep the answer strictly focused on the exact system mentioned.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER (strictly from context):

"""

    return {
        "answer": context,
        # "sources": docs,
        "debug_context": [d["text"] for d in docs]
    }