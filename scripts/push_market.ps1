# push_market.ps1  -- RETIRED (D-050, 2026-10-15)
#
# This was the legacy direct-push entry: git pull -> mis_fetcher -> commit data/market.json ->
# "git push origin main" with "-X ours" retries. It bypassed market_guard, publish_gate and the
# product policy, so it is permanently disabled. It does nothing except print an error and exit 1,
# with or without -Force. It does not create logs, read or write data, fetch, run git, or start any
# other process. This file does not change or disable external runners or scheduled tasks.
# Production writer switching remains subject to separate approval and verification.
#
# -Force is still accepted so old callers get this clear refusal instead of a parameter error.

param([switch]$Force)

[Console]::Error.WriteLine("[push_market] RETIRED (D-050): this legacy direct-push entry is disabled and never fetches, writes or pushes. Use the reviewed workflow update-data.yml; -Force does not bypass this.")
exit 1
