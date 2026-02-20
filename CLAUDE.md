# Marketing Engine

LLM-powered content generation, approval queue, and cross-platform publishing for developer marketing.

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
├── enums.py             # Platform, ContentStream, ApprovalStatus, PublishStatus (StrEnum)
├── models.py            # Pydantic v2: ContentBrief, PostDraft, PipelineRun, WeeklyQueue
├── exceptions.py        # MarketingEngineError hierarchy (7 classes)
├── config.py            # YAML loading, env var overrides, platform credentials
├── db.py                # SQLite WAL, thread-local connections, CRUD + publish log
├── licensing.py         # HMAC keys (MKEN prefix, marketing-engine-v1 salt)
├── pipeline.py          # ContentPipeline: Research → Draft → Format → Queue
├── approval.py          # approve/edit/reject/review queue
├── export.py            # JSON or Markdown export of approved posts
├── formatters.py        # Rich tables/panels for CLI output
├── cli.py               # Typer CLI (13 commands)
├── llm/
│   ├── base.py          # LLMClient ABC + MockLLMClient
│   └── ollama.py        # OllamaClient (httpx POST)
├── agents/
│   ├── base.py          # BaseAgent ABC (JSON fence stripping, retry)
│   ├── research.py      # ResearchAgent → list[ContentBrief]
│   ├── draft.py         # DraftAgent → {content, cta_url, hashtags}
│   ├── format.py        # FormatAgent → platform-specific with limit enforcement
│   └── queue.py         # QueueAgent (deterministic, no LLM)
└── publishers/
    ├── __init__.py      # Package exports
    ├── base.py          # PlatformPublisher ABC + DryRunPublisher + factory
    ├── result.py        # PublishResult model
    ├── twitter.py       # TwitterPublisher (v2 API, Bearer token)
    ├── linkedin.py      # LinkedInPublisher (UGC Posts API)
    ├── reddit.py        # RedditPublisher (OAuth2 password grant)
    └── scheduler.py     # publish_due_posts + publish_single
```

## Pipeline Flow

```
ResearchAgent → DraftAgent → FormatAgent → QueueAgent → DB
                                                         ↓
                                              CLI: review → approve/edit/reject → export
                                                                                    ↓
                                                              CLI: publish → Platform APIs → publish_log
```

## Key Commands

```bash
marketing-engine generate --dry-run          # Mock pipeline run
marketing-engine generate --week 2025-03-03  # Real LLM generation
marketing-engine review                      # Interactive approval
marketing-engine queue --status pending      # View queue
marketing-engine export --format markdown    # Export approved posts
marketing-engine publish --dry-run           # Simulate publishing (PRO)
marketing-engine publish-one POST_ID         # Publish single post (PRO)
marketing-engine publish-status              # View publish history
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
| `MKEN_TWITTER_BEARER_TOKEN` | (none) | Twitter v2 API bearer token |
| `MKEN_LINKEDIN_ACCESS_TOKEN` | (none) | LinkedIn OAuth2 access token |
| `MKEN_LINKEDIN_PERSON_ID` | (none) | LinkedIn person URN ID |
| `MKEN_REDDIT_CLIENT_ID` | (none) | Reddit app client ID |
| `MKEN_REDDIT_CLIENT_SECRET` | (none) | Reddit app client secret |
| `MKEN_REDDIT_USERNAME` | (none) | Reddit username |
| `MKEN_REDDIT_PASSWORD` | (none) | Reddit password |

## Testing

- 581 tests, 89% coverage, 80% gate
- All LLM calls mocked via `MockLLMClient`
- All API calls mocked via httpx patches
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
- Publishing gated behind PRO license tier
- Publishers use `edited_content or content` (effective content pattern)
