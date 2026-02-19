# Marketing Engine

**Autonomous cross-platform content creation, batch approval, and scheduled posting.**

A monorepo containing the Marketing Engine orchestration layer and three AI-powered YouTube channel pipelines. Forge workflows generate content, queue for weekly batch approval, and publish on schedule.

---

## Repository Structure

```
marketing-engine/
├── docs/
│   └── DESIGN.md                        ← Marketing Engine design spec
├── channels/
│   ├── story-fire/                      ← World folklore Shorts (Storyteller + Dog)
│   │   ├── README.md
│   │   └── docs/DESIGN.md
│   ├── new-eden-whispers/               ← EVE Online Chronicles Shorts
│   │   ├── README.md
│   │   └── docs/DESIGN.md
│   └── holmes-wisdom/                   ← Ernest Holmes public domain Shorts
│       ├── README.md
│       └── docs/DESIGN.md
├── README.md
└── LICENSE
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   MARKETING ENGINE                        │
│                                                           │
│  Research Agent → Draft Agent → Format Agent → Queue      │
│       ↓              ↓              ↓            ↓        │
│  Trends/activity  Raw posts    Platform-fit   Schedule    │
│                                                           │
│              APPROVAL QUEUE (weekly batch review)          │
│                         ↓                                 │
│              Scheduler Agent → Publish                    │
│                         ↓                                 │
│     ┌──────┬──────────┬────────┬─────────┬──────────┐    │
│     │  X   │ LinkedIn │ Reddit │ YouTube │  TikTok  │    │
│     └──────┴──────────┴────────┴─────────┴──────────┘    │
│                                                           │
│  CONTENT SOURCES:                                         │
│  ┌──────────────┐ ┌────────────────┐ ┌──────────────┐   │
│  │  Story Fire   │ │  New Eden      │ │   Holmes     │   │
│  │  (folklore)   │ │  Whispers      │ │   Wisdom     │   │
│  │              │ │  (EVE lore)    │ │  (SoM)       │   │
│  └──────────────┘ └────────────────┘ └──────────────┘   │
│  + Project marketing (GitHub repos, launches, updates)   │
└─────────────────────────────────────────────────────────┘
```

---

## Channels

### [Story Fire](channels/story-fire/) — World Folklore

AI-powered YouTube Shorts in the spirit of Jim Henson's *The Storyteller*. Two-character narration (Storyteller + Dog), culture-specific Stable Diffusion visuals, Gorgon multi-agent orchestration. 3,000+ public domain folk tales from every culture.

### [New Eden Whispers](channels/new-eden-whispers/) — EVE Online Lore

Cinematic YouTube Shorts from CCP's EVE Online Chronicles. 200+ chronicles, faction-matched visuals with mood color grading, epic narration. CCP content policy compliant — ad monetization allowed.

### [Holmes Wisdom](channels/holmes-wisdom/) — Science of Mind

Ernest Holmes' pre-1929 public domain writings transformed into YouTube Shorts. Fully local pipeline (Ollama + Piper TTS + FFmpeg). Mood-matched gradient visuals. Top-of-funnel for courses and memberships.

---

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
Drives traffic to YouTube channels (see Channels above).

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
| Monday evening | Review the weekly queue: approve / edit / reject per post |
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

## Status

Pre-implementation. Design specs complete for all components:
- [Marketing Engine design](docs/DESIGN.md)
- [Story Fire design](channels/story-fire/docs/DESIGN.md)
- [New Eden Whispers design](channels/new-eden-whispers/docs/DESIGN.md)
- [Holmes Wisdom design](channels/holmes-wisdom/docs/DESIGN.md)

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
