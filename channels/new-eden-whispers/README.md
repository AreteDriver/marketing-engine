# New Eden Whispers

**AI-powered EVE Online Chronicles YouTube Shorts pipeline.**

An automated content pipeline that transforms CCP's EVE Online Chronicles into cinematic YouTube Shorts. LLM-powered scene extraction, faction-matched visuals, epic narration, and burned-in captions.

---

## Architecture

```
EVE Fiction Portal → Scraper → Ollama (scene extraction) → Script JSON
                                                              ↓
EVE Visual Library → Visual Selector → FFmpeg Assembly ← TTS Narration
                                            ↓                    ↑
                                       Final MP4 ← Whisper Captions
```

## Content Library

- 200+ Chronicles spanning 20+ years of EVE lore
- Short Stories, Lore Articles, Scientific Articles
- Organized by era (YC102-YC126) and faction

## CCP Content Policy

Per CCP's Content Creation Terms:
- Monetization via passive ads (YouTube Shorts) is allowed
- Use of storylines, characters, and in-game footage is allowed
- Content must not be paywalled or sold directly

## Tech Stack

| Component | Tool |
|-----------|------|
| Scraper | Python (requests + BeautifulSoup) |
| LLM | Ollama (Animus) |
| TTS | Piper (free) / ElevenLabs (premium) |
| Visuals | EVE screenshots + Stable Diffusion |
| Captions | Whisper |
| Assembly | FFmpeg |
| Orchestration | Python pipeline |

## Visual System

Faction-matched visuals with mood-based color grading:
- Amarr (golden, religious), Caldari (blue-gray, corporate)
- Gallente (green, democratic), Minmatar (rust-fire, tribal)
- Jove/Drifter (alien, mysterious), Pirate factions

## Growth Path

| Milestone | Action |
|-----------|--------|
| 500 subs | Weekly long-form deep dives |
| 5K subs | Apply for CCP Partnership Program |
| 10K subs | Fanfest coverage potential |

## Status

Pre-implementation. Design spec complete. See [docs/DESIGN.md](docs/DESIGN.md).

## Related Projects

| Project | Relationship |
|---------|-------------|
| [Animus](https://github.com/AreteDriver/animus) | Parent system |
| [EVE_Collection](https://github.com/AreteDriver/EVE_Collection) | EVE tooling monorepo |
| [Marketing Engine](https://github.com/AreteDriver/marketing-engine) | Cross-platform posting |

## License

MIT
