# claude-code-cache-ttl-advisor

Claude Code plugin with one skill. It reads the token usage that Claude Code already logged in your local session transcripts (no API calls, no tokens spent) and tells you whether a 5-minute or 1-hour prompt-cache TTL is cheaper for main sessions and for subagents.

## What the script does

It makes no API calls and spends no tokens. It only reads local files and does arithmetic.

1. Finds every `.jsonl` transcript under `~/.claude/projects`, at any depth. A file directly under a project folder is a main session; every deeper file (subagents, workflow agents, subagents of subagents) is in the subagent group. Claude Code sets the TTL separately for these two groups.
2. From each transcript, takes the assistant records and keeps one per API call (by `message.id`). For each call it reads the logged `usage`: cache write tokens, cache read tokens, and which TTL was used (`ephemeral_5m` or `ephemeral_1h`). A call with only reads uses the TTL of the transcript's last write.
3. Prices every call twice, once as if the TTL was 5 minutes and once as if it was 1 hour, with that call's model prices:
   - Gap from the previous call ≤ 5 min or > 1 h: same tokens under both TTLs; only the write price differs (1.25× vs 2× base input).
   - Gap of 5 min – 1 h: the previous call's cached prefix expires under 5m and survives under 1h. The script moves that prefix from write to read (or back) for the TTL that did not run.
4. Adds the costs per group, per month and per model, prints a table, and recommends `CLAUDE_CODE_PROMPT_CACHE_TTL` and `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`.

Costs are at API list prices. On a subscription they compare usage, not a bill. Output tokens and uncached input do not depend on the TTL, so they are left out. The script does not model compaction or cache shared between agents.

## Install from GitHub

Claude Code installs plugins from a GitHub repository in two steps: register the repository, then install the plugin from it. The repository carries its own `.claude-plugin/marketplace.json`, so no separate marketplace is involved.

In Claude Code:

```
/plugin marketplace add nickwinder/claude-code-cache-ttl-advisor
/plugin install claude-code-cache-ttl-advisor@claude-code-cache-ttl-advisor
```

Or from a shell:

```bash
claude plugin marketplace add nickwinder/claude-code-cache-ttl-advisor
claude plugin install claude-code-cache-ttl-advisor@claude-code-cache-ttl-advisor
```

The repository is private: git on your machine must already be able to clone it (`gh auth login && gh auth setup-git`, or an SSH key in ssh-agent).

## Without the plugin system

Clone the repository and copy the skill folder:

```bash
git clone git@github.com:nickwinder/claude-code-cache-ttl-advisor.git
cp -R claude-code-cache-ttl-advisor/skills/claude-code-cache-ttl-advisor ~/.claude/skills/
```

## Use

Ask Claude "what prompt cache TTL should I use?", or run the script directly:

```bash
python3 skills/claude-code-cache-ttl-advisor/scripts/ttl_advisor.py [--days N]
```
