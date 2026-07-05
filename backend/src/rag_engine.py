"""
Simple RAG component (Step 2 requirement: "Simple RAG component using
policy information").

Deliberately in-memory + numpy cosine similarity instead of a vector DB.
For a handful of policy documents that's the right amount of engineering —
swap in Pinecone or OpenSearch Serverless later if the knowledge base grows
past what fits comfortably in memory. Adhi: you've already built the
Pinecone version for TownRise/MediGuard, no need to repeat it here.
"""
import os




class PolicyRAG:
    def __init__(self, bedrock_client, policy_dir="policy_knowledge"):
        self.bedrock = bedrock_client
        self.policy_dir = policy_dir
        self.chunks = []       # list[str]
        self.vectors = []      # list[list[float]]

    def build_index(self):
        chunks = []
        for fname in sorted(os.listdir(self.policy_dir)):
            path = os.path.join(self.policy_dir, fname)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
                chunks.append(para)

        if not chunks:
            raise ValueError(f"No policy documents found in {self.policy_dir}")

        vectors = [self.bedrock.embed(c) for c in chunks]
        self.chunks = chunks
        self.vectors = vectors
        return len(chunks)

    def retrieve(self, query, top_k=2):
        if not self.vectors:
            raise RuntimeError("Call build_index() before retrieve()")

        query_vec = self.bedrock.embed(query)
        
        similarities = []
        for idx, doc_vec in enumerate(self.vectors):
            dot_product = sum(x*y for x, y in zip(doc_vec, query_vec))
            mag_doc = sum(x*x for x in doc_vec) ** 0.5
            mag_query = sum(x*x for x in query_vec) ** 0.5
            sim = dot_product / (mag_doc * mag_query) if mag_doc and mag_query else 0.0
            similarities.append((sim, idx))

        # Sort descending by similarity
        similarities.sort(key=lambda x: x[0], reverse=True)
        top_idx = [idx for sim, idx in similarities[:top_k]]
        return [self.chunks[i] for i in top_idx]

    def retrieve_as_context(self, query, top_k=2):
        results = self.retrieve(query, top_k=top_k)
        return "\n---\n".join(results)

