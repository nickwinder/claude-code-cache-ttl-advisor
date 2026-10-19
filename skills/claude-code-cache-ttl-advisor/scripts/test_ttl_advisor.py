import datetime as dt, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ttl_advisor import price_both_ttls

t0 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
u = lambda w, r, h1=False: {"cache_creation_input_tokens": w, "cache_read_input_tokens": r,
                            "cache_creation": {"ephemeral_1h_input_tokens" if h1 else "ephemeral_5m_input_tokens": w}}
M = "claude-sonnet-5"  # $2 base, 0.1x read

# 5m run, 10 min gap: 1M prefix rewritten -> under 1h it is a read.
out = list(price_both_ttls([(t0, u(1_000_000, 0), M), (t0 + dt.timedelta(minutes=10), u(1_000_000, 0), M)]))
assert abs(out[1][2] - 2.5) < 1e-9 and abs(out[1][3] - 0.2) < 1e-9 and out[1][4]
# 1h run, 10 min gap: 1M read -> under 5m it is a rewrite.
out = list(price_both_ttls([(t0, u(1_000_000, 0, True), M), (t0 + dt.timedelta(minutes=10), u(0, 1_000_000), M)]))
assert abs(out[1][2] - 2.5) < 1e-9 and abs(out[1][3] - 0.2) < 1e-9
# 2 h gap: expired under both, only write price differs.
out = list(price_both_ttls([(t0, u(1, 0), M), (t0 + dt.timedelta(hours=2), u(1_000_000, 0), M)]))
assert abs(out[1][2] - 2.5) < 1e-9 and abs(out[1][3] - 4.0) < 1e-9 and not out[1][4]
print("ok")
