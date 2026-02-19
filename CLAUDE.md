# Marketing Engine

LLM-powered content generation, approval queue, and cross-platform export for developer marketing.

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v --cov=marketing_engine --cov-report=term-missing
ruff check src/ tests/ && ruff format --check src/ tests/
```

## Architecture

```
src/marketing_engine/
├── __init__.py          # Version: 0.1.0
├── __main__.py          # CLI entry point
├── enums.py             # Platform, ContentStream, ApprovalStatus (StrEnum)
├── models.py            # Pydantic v2: ContentBrief, PostDraft, PipelineRun, WeeklyQueue
├── exceptions.py        # MarketingEngineError hierarchy (6 classes)
├── config.py            # YAML loading, env var overrides (MKEN_* prefix)
├── db.py                # SQLite WAL, thread-local connections, CRUD
├── licensing.py         # HMAC keys (MKEN prefix, marketing-engine-v1 salt)
├── pipeline.py          # ContentPipeline: Research → Draft → Format → Queue
├── approval.py          # approve/edit/reject/review queue
├── export.py            # JSON or Markdown export of approved posts
├── formatters.py        # Rich tables/panels for CLI output
├── cli.py               # Typer CLI (10 commands)
├── llm/
│   ├── base.py          # LLMClient ABC + MockLLMClient
│   └── ollama.py        # OllamaClient (httpx POST)
└── agents/
    ├── base.py          # BaseAgent ABC (JSON fence stripping, retry)
    ├── research.py      # ResearchAgent → list[ContentBrief]
    ├── draft.py         # DraftAgent → {content, cta_url, hashtags}
    ├── format.py        # FormatAgent → platform-specific with limit enforcement
    └── queue.py         # QueueAgent (deterministic, no LLM)
```

## Pipeline Flow

```
ResearchAgent → DraftAgent → FormatAgent → QueueAgent → DB
                                                         ↓
                                              CLI: review → approve/edit/reject → export
```

## Key Commands

```bash
marketing-engine generate --dry-run          # Mock pipeline run
marketing-engine generate --week 2025-03-03  # Real LLM generation
marketing-engine review                      # Interactive approval
marketing-engine queue --status pending      # View queue
marketing-engine export --format markdown    # Export approved posts
marketing-engine status                      # Config + license info
marketing-engine init                        # Create default configs
marketing-engine history                     # Pipeline run history
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MKEN_CONFIG_DIR` | `./configs/` | Config YAML directory |
| `MKEN_DB_PATH` | `~/.local/share/marketing-engine/marketing.db` | SQLite database |
| `MKEN_LLM_PROVIDER` | `ollama` | LLM provider |
| `MKEN_LLM_MODEL` | `llama3.2` | LLM model name |
| `MKEN_LICENSE` | (none) | License key |

## Testing

- 345 tests, 87% coverage, 80% gate
- All LLM calls mocked via `MockLLMClient`
- All DB tests use `tmp_path` fixtures
- `reset_database()` clears the `@lru_cache` singleton between tests

## Conventions

- Python 3.11+, `X | None` type hints (no `Optional`)
- `from __future__ import annotations` in modules with complex types
- Ruff: E/F/W/I/N/UP/B/A/SIM rules, 100 char line limit
- SQLite WAL mode, `check_same_thread=False`
- JSON fence stripping + one retry on LLM parse failures
- Deterministic QueueAgent (pure Python, no LLM)
- HMAC license keys: `MKEN-TIER-RANDOM-CHECKSUM`
