# scripts

Operational and one-off scripts. Things that are run by a person, not by the scheduler.

Expected inhabitants:

| Script | Purpose |
|---|---|
| `seed_catalogue.py` | Load the seed lists in `data/seed/` into `core` |
| `run_connector.py` | Run one connector by `source_key`, for debugging |
| `replay_parsers.py` | Re-derive evidence units from stored raw payloads after a parser change |
| `rebuild_verdicts.py` | Re-run fusion for every configuration without re-ingesting |
| `export_metrics.py` | Write the latest `eval_run` row for the metrics page |
| `warm_up.py` | Pre-warm the free-tier database and API before a demo — **run this before presenting** |

Two rules: every script is idempotent, and every script that writes takes `--dry-run`.
