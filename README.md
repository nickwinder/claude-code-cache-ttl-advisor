# claude-code-cache-ttl-advisor

Claude Code plugin with one skill. It reads the token usage that Claude Code already logged in your local session transcripts (no API calls, no tokens spent) and tells you whether a 5-minute or 1-hour prompt-cache TTL is cheaper for main sessions and for subagents.

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
