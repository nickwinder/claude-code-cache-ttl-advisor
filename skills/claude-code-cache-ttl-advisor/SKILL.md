---
name: claude-code-cache-ttl-advisor
description: Read the token usage already logged in every Claude Code session transcript (main sessions, subagents, workflow agents, nested subagents) and price prompt caching under a 5-minute and a 1-hour TTL, then recommend CLAUDE_CODE_PROMPT_CACHE_TTL and CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL. Use when asked "what cache TTL should I use", "am I losing tokens to cache expiry", "should subagents use a 1h cache", or to audit prompt-cache cost.
---

# Claude Code cache TTL advisor

Run:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/ttl_advisor.py" [--days N] [--root ~/.claude/projects]
```

It prints a markdown table per TTL bucket (`main`, `subagent`) with ALL, per-month and per-model rows, then one recommended setting per bucket. Show the table to the user as is, then state the two recommendations.

## How it works

- It makes no API calls and costs no tokens. It only reads the `usage` fields that Claude Code already wrote to the local `.jsonl` transcripts, then does arithmetic.

- Claude Code has two TTL buckets: the main conversation (`<project>/<session>.jsonl`) and everything else (any `.jsonl` deeper, found recursively — subagents, `subagents/workflows/…`, nested agents). Each takes only `5m` or `1h`.
- Per API call (deduplicated by `message.id`), it reads `cache_creation_input_tokens`, `cache_read_input_tokens`, and which TTL ran (`cache_creation.ephemeral_{5m,1h}_input_tokens`).
- A gap of 5–60 minutes since the previous call in the same transcript is where the TTLs differ: the previous cached prefix is rewritten under 5m and read under 1h. The script moves that prefix between write and read for the TTL that did not run. Other calls change only the write price (1.25x vs 2x).
- Prices are per model from the Anthropic prompt-caching page, in `PRICES`. An unknown model stops the script; add its price.

## Limits

- Dollars are API list prices; on a subscription they measure usage, not a bill.
- The gap is between API calls, so it includes long tool runs and idle time.
- It does not model compaction or cache sharing between agents.

Test: `python3 scripts/test_ttl_advisor.py`.
