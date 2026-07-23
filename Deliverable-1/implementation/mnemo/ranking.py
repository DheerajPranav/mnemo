"""
ranking.py — hand-specified multi-signal ranker over currently-valid facts. [M3]

The baseline ranked on ONE signal (lexical cosine) over an unfiltered global index, which is why a
stale/foreign/PII chunk could sit at rank 1 (design/failure_analysis.md). Mnemo ranks only what the
retrieval layer already guaranteed is tenant-local and currently-valid, and combines interpretable
signals:

  lexical    — TF-IDF cosine of query vs fact text (the relevance signal, self-contained here so the
               domain imports no experiment code — invariant I6)
  account    — soft grounding: same-account facts are boosted (not hard-filtered — see retrieval.py)
  recency    — small tiebreak toward the more recently recorded fact

Deliberately NOT a signal: "similarity to a stale fact." Validity is enforced upstream (I3), not
patched in the ranker. `lexical` is exposed separately so injection.py can abstain on true relevance
rather than on the account-boosted score.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass

from .repository import Fact

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# signal weights — hand-specified and interpretable (design/system_design.md ranker section)
W_ACCOUNT = 0.25   # same-account grounding bonus
W_RECENCY = 0.05   # newer-fact tiebreak

# Stopwords. M3 recovery: over a small candidate corpus, function words ("the/for/is/on") get high
# idf, so a query sharing only stopwords with a fact scored 0.32+ cosine and defeated the abstain
# threshold — cold-start queries q09/q10 "answered" from irrelevant facts (gate G2 coldstart=1.0).
# Removing stopwords makes lexical similarity measure CONTENT overlap, so a query with no content-word
# match falls below threshold and the system abstains. See .genesis/checkpoints/M3.md.
_STOPWORDS = frozenset("""
a an and are as at be by do does for from has have i in is it its of on or that the their they this
to we what when where which who will with you your about not need
""".split())


def tokenize(text):
    """Content tokens only — lowercase word tokens, stopwords and single characters removed.

    Dropping length-1 tokens kills the possessive/contraction artifact: "Acme's" and "Let's" both
    yield a stray "s", which made the filler "Let's schedule the next call" spuriously match a query
    containing "Acme's" (cold-start q10). Single-character tokens carry no content."""
    return [t for t in _TOKEN_RE.findall(text.lower())
            if len(t) > 1 and t not in _STOPWORDS]


@dataclass
class Ranked:
    score: float       # combined score used for ordering
    lexical: float     # raw lexical relevance (used for the abstain decision)
    fact: Fact


class _Tfidf:
    def __init__(self, docs_tokens):
        n = len(docs_tokens)
        df = Counter()
        for toks in docs_tokens:
            for t in set(toks):
                df[t] += 1
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}

    def vec(self, toks):
        if not toks:
            return {}
        tf = Counter(toks)
        return {t: (c / len(toks)) * self.idf.get(t, 0.0) for t, c in tf.items()}


def _cosine(a, b):
    if not a or not b:
        return 0.0
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    dot = sum(w * large.get(t, 0.0) for t, w in small.items())
    return dot / (na * nb)


def _doc_tokens(fact):
    """Token bag for a fact = its text PLUS its typed subject slot. Using the subject is the payoff
    of M2's typed extraction: the current SSO fact m006 ("put it in — non-negotiable") never repeats
    the word 'SSO' in its text, but its subject slot is 'sso', so it matches a query about SSO. Raw
    chunks (the baseline) had no such slot."""
    return tokenize(fact.text) + tokenize(fact.subject)


def rank(query, account, facts):
    """Rank currently-valid `facts` for `query`. Returns a list[Ranked], best first, deterministic.

    The account NAME is removed from the lexical bag (query and docs): "Acme" is *grounding*, handled
    by the structured W_ACCOUNT signal, not free-text content. Otherwise the shared account token gave
    every Acme fact a lexical floor, so a cold-start Acme query (q10, a topic with no fact) never fell
    below the abstain threshold. Grounding stays; the account name stops masquerading as content.
    """
    acct_tokens = set(tokenize(account)) if account else set()

    def strip(toks):
        return [t for t in toks if t not in acct_tokens]

    docs = [strip(_doc_tokens(f)) for f in facts]
    idf = _Tfidf(docs)
    qv = idf.vec(strip(tokenize(query)))

    # recency: rank facts by recorded_at so the newest gets the full W_RECENCY bonus
    order = sorted(range(len(facts)), key=lambda i: facts[i].recorded_at)
    recency_rank = {i: (pos / max(1, len(facts) - 1)) for pos, i in enumerate(order)}

    ranked = []
    for i, (f, d) in enumerate(zip(facts, docs)):
        lex = _cosine(qv, idf.vec(d))
        acct_bonus = W_ACCOUNT if (account and f.account == account) else 0.0
        rec_bonus = W_RECENCY * recency_rank[i]
        score = lex * (1.0 + acct_bonus) + lex * rec_bonus
        ranked.append(Ranked(score=score, lexical=lex, fact=f))

    ranked.sort(key=lambda r: (-r.score, r.fact.id))  # deterministic tie-break by id
    return ranked
