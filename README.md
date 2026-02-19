# Marketing Engine

**Autonomous cross-platform content creation, batch approval, and scheduled posting.**

A Forge workflow that generates platform-optimized marketing posts for two content streams, queues them for weekly batch approval, and publishes approved posts on schedule.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  WEEKLY CYCLE                     │
│                                                   │
│  Research Agent → Draft Agent → Format Agent      │
│       ↓              ↓              ↓             │
│  Trending topics  Raw posts    Platform-specific  │
│  Project updates  per stream   versions           │
│                                                   │
│              Queue Agent → APPROVAL QUEUE          │
│                    ↓         (weekly batch)        │
│              Scheduler Agent                       │
│                    ↓                               │
│     ┌──────┬──────────┬────────┬────────┬───────┐ │
│     │  X   │ LinkedIn │ Reddit │ YouTube│ TikTok│ │
│     └──────┴──────────┴────────┴────────┴───────┘ │
└─────────────────────────────────────────────────┘
```

## Content Streams

### Stream 1: Project Marketing
Drives traffic to GitHub repos, launches, and updates.

| Project | Content Angles |
|---------|---------------|
| BenchGoblins | Launch announcements, feature highlights, fantasy sports hot takes |
| Animus | Architecture deep-dives, "building in public" updates |
| LinuxTools | Tool releases, OCR demos, Steam Deck compatibility |
| EVE_Collection | Game dev progress, Argus updates, EVE community engagement |
| claudemd-forge | Usage tips, developer productivity angle |

### Stream 2: Media Engine
Drives traffic to YouTube channels.

| Channel | Content Angles |
|---------|---------------|
| Story Fire | Episode teasers, folklore facts, mythology threads |
| New Eden Whispers | EVE lore snippets, in-universe teasers |
| Holmes Wisdom | Deduction puzzles, wisdom quotes, episode highlights |

---

## Agents

| Agent | Role |
|-------|------|
| **Research** | GitHub activity, YouTube analytics, platform trends, competitor intel |
| **Draft** | Raw post text per content stream with clear CTAs |
| **Format** | Platform-specific versions (X, LinkedIn, Reddit, YouTube, TikTok) |
| **Queue** | Weekly schedule builder with optimal posting windows |
| **Scheduler** | Publishes approved posts via platform APIs on schedule |

---

## Weekly Workflow

| Day | Activity |
|-----|----------|
| Monday | Forge runs Research → Draft → Format → Queue pipeline |
| Monday evening | You review the weekly queue: approve / edit / reject per post |
| Tuesday-Sunday | Scheduler publishes approved content at assigned times |
| Sunday | Analytics collection for next week's optimization |

---

## Platform APIs

| Platform | API | Auth | Free Tier |
|----------|-----|------|-----------|
| Twitter/X | v2 | OAuth 2.0 PKCE | 1,500 tweets/mo |
| LinkedIn | Marketing API | OAuth 2.0 | App review required (1-2 weeks) |
| Reddit | Reddit API | OAuth 2.0 | Free, 60 req/min |
| YouTube | Data API v3 | OAuth 2.0 | 10K units/day (~6 uploads) |
| TikTok | Content Posting API | OAuth 2.0 | App review required (2-4 weeks) |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python |
| Orchestration | Animus Forge (Gorgon) |
| LLM | Claude API / Ollama |
| Scheduling | Cron or persistent daemon |
| State | SQLite (Forge checkpoints) |
| Config | Declarative YAML |

---

## Estimated Volume

| Platform | Posts/Week |
|----------|-----------|
| Twitter/X | 7-10 |
| LinkedIn | 3-5 |
| Reddit | 3-5 |
| YouTube (full) | 10-12 |
| YouTube (Shorts) | 5-8 |
| TikTok | 5-7 |
| **Total** | **33-47** |

---

## Status

Pre-implementation. Design spec complete. See [docs/DESIGN.md](docs/DESIGN.md) for full architecture.

---

## Related Projects

| Project | Relationship |
|---------|-------------|
| [Animus](https://github.com/AreteDriver/animus) | Parent system — Core routes intents to Forge |
| [Gorgon](https://github.com/AreteDriver/Gorgon) | Orchestration engine powering Forge workflows |
| [BenchGoblins](https://github.com/AreteDriver/BenchGoblins) | Primary monetization target for project marketing |

---

## License

MIT
