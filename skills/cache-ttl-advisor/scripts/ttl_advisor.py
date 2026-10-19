#!/usr/bin/env python3
"""Replay Claude Code transcripts and price prompt caching under a 5m and a 1h TTL.

Walks every *.jsonl under the projects dir at any depth, so subagents, workflow
agents and subagents of subagents are all included. Claude Code has two TTL
buckets: the main conversation (<project>/<session>.jsonl) and everything else.
"""
import argparse, collections, datetime as dt, json, sys
from pathlib import Path

# $/MTok base input price, cache-read multiplier. Source:
# platform.claude.com/docs/en/build-with-claude/prompt-caching (read 2026-10-20).
# Longest key that is a substring of the model id wins.
PRICES = {
    "fable-5-1": (10, 0.025), "mythos-5-1": (10, 0.025),
    "fable-5": (10, 0.1), "mythos-5": (10, 0.1),
    "opus-5-5": (4, 0.05), "opus-5": (5, 0.1),
    "opus-4-8": (5, 0.1), "opus-4-7": (5, 0.1), "opus-4-6": (5, 0.1), "opus-4-5": (5, 0.1),
    "opus-4-1": (15, 0.1), "opus-4-2": (15, 0.1),
    "sonnet-5-5": (2, 0.05), "sonnet-5": (2, 0.1), "sonnet-4": (3, 0.1),
    "haiku-5-5": (0.1, 0.1), "haiku-4-5": (1, 0.1), "3-5-haiku": (0.8, 0.1),
}
W5, W1 = 1.25, 2.0
TTL = {"5m": 300, "1h": 3600}


def price(model):
    hits = [k for k in PRICES if k in model]
    if not hits:
        raise SystemExit(f"error: no price for model {model!r}; add it to PRICES")
    return PRICES[max(hits, key=len)]


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def api_calls(path):
    """One entry per API response; streamed chunks share message.id."""
    seen = {}
    with open(path, errors="ignore") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            m = r.get("message") or {}
            u = m.get("usage")
            if r.get("type") != "assistant" or not u:
                continue
            if not (u.get("cache_creation_input_tokens") or u.get("cache_read_input_tokens")):
                continue
            seen[m.get("id") or r.get("uuid")] = (ts(r["timestamp"]), u, m.get("model", ""))
    return sorted(seen.values(), key=lambda c: c[0])


def replay(calls):
    """Yield (time, model, cost_5m, cost_1h, gap_hit) per call, in dollars.

    Calls whose gap since the previous call is outside (5m, 1h] cost the same
    under both TTLs apart from the write price. Inside that window the cached
    prefix expires under 5m but survives under 1h, so that prefix moves between
    write and read depending on which TTL actually ran.
    """
    prev = None
    ran_1h = False  # a read-only call reports no TTL; it inherits the last write's
    for t, u, model in calls:
        base, rmul = price(model)
        w = u.get("cache_creation_input_tokens") or 0
        r = u.get("cache_read_input_tokens") or 0
        cc = u.get("cache_creation") or {}
        h1, m5 = cc.get("ephemeral_1h_input_tokens") or 0, cc.get("ephemeral_5m_input_tokens") or 0
        if h1 or m5:
            ran_1h = h1 > m5
        w5, r5, w1, r1 = w, r, w, r
        hit = False
        if prev:
            gap = (t - prev[0]).total_seconds()
            if TTL["5m"] < gap <= TTL["1h"]:
                prefix = (prev[1].get("cache_read_input_tokens") or 0) + (prev[1].get("cache_creation_input_tokens") or 0)
                if ran_1h:  # observed read; under 5m it would be rewritten
                    moved = min(r, prefix); w5, r5 = w + moved, r - moved
                else:       # observed rewrite; under 1h it would be read
                    moved = min(w, prefix); w1, r1 = w - moved, r + moved
                hit = moved > 0
        prev = (t, u)
        yield t, model, base * (W5 * w5 + rmul * r5) / 1e6, base * (W1 * w1 + rmul * r1) / 1e6, hit


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(Path.home() / ".claude/projects"))
    ap.add_argument("--days", type=int, help="only API calls in the last N days")
    a = ap.parse_args()
    root = Path(a.root)
    if not root.is_dir():
        raise SystemExit(f"error: {root} is not a directory")
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=a.days) if a.days else None

    rows = collections.defaultdict(lambda: [0, 0, 0.0, 0.0, 0])  # files, calls, 5m, 1h, gap hits
    agents = collections.Counter()  # bucket -> agents cheaper on 1h
    for p in root.rglob("*.jsonl"):
        bucket = "main" if len(p.relative_to(root).parts) == 2 else "subagent"
        a5 = a1 = 0.0
        counted = False
        for t, model, c5, c1, hit in replay(api_calls(p)):
            if since and t < since:
                continue
            counted = True
            for key in ((bucket, "ALL"), (bucket, f"month {t:%Y-%m}"), (bucket, f"model {model}")):
                row = rows[key]; row[1] += 1; row[2] += c5; row[3] += c1; row[4] += hit
            a5 += c5; a1 += c1
        if counted:
            for key in rows:
                if key[0] == bucket and key[1] == "ALL":
                    rows[key][0] += 1
            agents[bucket] += a1 < a5
            agents[bucket + "_n"] += 1

    if not rows:
        raise SystemExit(f"error: no transcripts with cache usage under {root}")
    print("| Bucket | Slice | Calls | Gaps 5m–1h | Cost @5m | Cost @1h | 1h vs 5m | Best |")
    print("|---|---|---:|---:|---:|---:|---:|---|")
    for (bucket, sl) in sorted(rows, key=lambda k: (k[0], k[1] != "ALL", k[1])):
        _, n, c5, c1, hits = rows[(bucket, sl)]
        d = (c1 - c5) / c5 if c5 else 0
        print(f"| {bucket} | {sl} | {n:,} | {hits:,} | ${c5:,.2f} | ${c1:,.2f} | {d:+.1%} | {'1h' if c1 < c5 else '5m'} |")
    print()
    env = {"main": "CLAUDE_CODE_PROMPT_CACHE_TTL", "subagent": "CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL"}
    for b in ("main", "subagent"):
        if (b, "ALL") in rows:
            _, _, c5, c1, _ = rows[(b, "ALL")]
            print(f"{b}: set {env[b]}={'1h' if c1 < c5 else '5m'} "
                  f"(saves ${abs(c1 - c5):,.2f}); {agents[b]}/{agents[b + '_n']} transcripts were cheaper on 1h")
    print("\nCosts are cache writes + cache reads at API list prices; output and uncached input are TTL-independent.")


if __name__ == "__main__":
    main()
