#!/usr/bin/env python3
"""
baseline.py — the deliberately naive conversational-memory baseline (Approach D from
../../reconstruction/failure_analysis.md): store every chunk, retrieve top-k by a single
similarity signal, inject in similarity order until a token budget is hit.

Deliberately absent (this is the point — their absence is what Deliverable 3 measures):
  * admission control            → everything is stored, incl. PII and duplicates
  * typed/resolved facts         → raw utterance chunks only
  * temporal validity            → no notion that a fact can stop being true
  * multi-signal ranking         → cosine similarity ONLY
  * tenant isolation             → one global index, no partition
  * consolidation / decay        → none

Similarity signal: cosine over TF-IDF vectors. Pure Python standard library — no numpy, no
model download, no API key — so the baseline is reproducible on any Python 3.8+ with a fixed
seed. The choice of a lexical signal (vs a dense embedding) is documented in
../baseline_protocol.md; the failures demonstrated here are structural, not signal-specific.
"""
import json
import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text):
    """Lowercase word tokens. The only text normalisation the naive baseline does."""
    return TOKEN_RE.findall(text.lower())


def estimate_tokens(text):
    """Cheap, deterministic token estimate for budgeting (~1.3 tokens per whitespace word,
    the common rule of thumb for English). Documented as an approximation in the protocol."""
    words = len(text.split())
    return int(round(words * 1.3))


class TfidfIndex:
    """A single global TF-IDF index over all memory chunks. No tenant partition, by design."""

    def __init__(self, memories):
        self.memories = memories
        self.docs_tokens = [tokenize(m["text"]) for m in memories]
        n = len(memories)
        # document frequency
        df = Counter()
        for toks in self.docs_tokens:
            for t in set(toks):
                df[t] += 1
        # smoothed idf
        self.idf = {t: math.log((1 + n) / (1 + df_t)) + 1.0 for t, df_t in df.items()}
        self.doc_vecs = [self._vec(toks) for toks in self.docs_tokens]
        self.doc_norms = [math.sqrt(sum(v * v for v in vec.values())) for vec in self.doc_vecs]

    def _vec(self, tokens):
        tf = Counter(tokens)
        return {t: (c / len(tokens)) * self.idf.get(t, 0.0) for t, c in tf.items()} if tokens else {}

    def _cosine(self, qvec, qnorm, idx):
        dvec, dnorm = self.doc_vecs[idx], self.doc_norms[idx]
        if qnorm == 0 or dnorm == 0:
            return 0.0
        # iterate over the smaller vector
        small, large = (qvec, dvec) if len(qvec) <= len(dvec) else (dvec, qvec)
        dot = sum(w * large.get(t, 0.0) for t, w in small.items())
        return dot / (qnorm * dnorm)

    def retrieve(self, query, k=5):
        """Top-k memories by cosine similarity. No filtering of any kind."""
        qtoks = tokenize(query)
        qvec = self._vec(qtoks)
        qnorm = math.sqrt(sum(v * v for v in qvec.values()))
        scored = [(self._cosine(qvec, qnorm, i), i) for i in range(len(self.memories))]
        scored.sort(key=lambda x: (-x[0], self.memories[x[1]]["id"]))  # deterministic tie-break
        return [(s, self.memories[i]) for s, i in scored[:k]]


def budgeted_injection(ranked, token_budget):
    """Naive context construction: walk top-k in similarity order, add each memory's text until
    the token budget would be exceeded. No importance ordering, no dedup, no position handling."""
    injected, used = [], 0
    for score, m in ranked:
        cost = estimate_tokens(m["text"])
        if used + cost > token_budget:
            break
        injected.append((score, m))
        used += cost
    return injected, used


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
