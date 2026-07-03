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
import numpy as np


class PolicyRAG:
    def __init__(self, bedrock_client, policy_dir="policy_knowledge"):
        self.bedrock = bedrock_client
        self.policy_dir = policy_dir
        self.chunks = []       # list[str]
        self.vectors = None    # np.ndarray, shape (n_chunks, dim)

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
        self.vectors = np.array(vectors, dtype=np.float32)
        return len(chunks)

    def retrieve(self, query, top_k=2):
        if self.vectors is None:
            raise RuntimeError("Call build_index() before retrieve()")

        query_vec = np.array(self.bedrock.embed(query), dtype=np.float32)
        norms = np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(query_vec)
        norms = np.where(norms == 0, 1e-8, norms)
        similarities = (self.vectors @ query_vec) / norms

        top_idx = np.argsort(similarities)[::-1][:top_k]
        return [self.chunks[i] for i in top_idx]

    def retrieve_as_context(self, query, top_k=2):
        results = self.retrieve(query, top_k=top_k)
        return "\n---\n".join(results)
