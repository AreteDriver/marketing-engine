# Timeless Clips

**Public domain clips reimagined as viral YouTube Shorts and TikTok content.**

An automated content pipeline that discovers compelling moments from the Internet Archive, Prelinger Archives, NASA, and other public domain sources, then transforms them into engaging vertical Shorts with original narration, captions, and visual treatment.

---

## Architecture

```
Internet Archive API → Discover → Download → Ollama (extract moment) → Script JSON
                                                                           ↓
                                         FFmpeg Compose ← TTS Narration (Piper/ElevenLabs)
                                              ↓                  ↑
                                         Final MP4 ← Whisper Captions
                                              ↑
                                    Color Grade + Text Overlays + 9:16 Crop
```

## Content Categories

| Category | Source | Examples |
|----------|--------|----------|
| Famous Speeches | Archive.org, LOC | FDR fireside chats, JFK inaugural, NASA comms |
| Classic Film Scenes | Archive.org Feature Films | Nosferatu, Metropolis, Chaplin, Keaton |
| Vintage Ads & PSAs | Prelinger Archives | Duck-and-cover, 1950s consumer ads, safety films |
| Newsreels | Archive.org, NASA | WWII footage, moon landing, historical events |
| Educational Films | Prelinger Archives | 1950s classroom, industrial, cold war |
| Quotes + Context | Multiple | Text overlay + era footage + original narration |

## Legal Framework

- **Public domain**: All pre-1929 US works, US government footage (NASA, military), Prelinger Archives
- **Creative Commons**: CC0 and CC-BY content from Wikimedia Commons and Archive.org
- **Fair use**: Short clips with transformative original narration/commentary for education and criticism
- **Red line**: No post-1929 copyrighted material without substantial transformative commentary

## Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| Discovery | Internet Archive API (requests) | Free |
| LLM | Ollama (moment extraction + script) | Free |
| TTS | Piper (MVP) / ElevenLabs (premium) | Free / ~$5/mo |
| Captions | Whisper | Free |
| Assembly | FFmpeg | Free |
| Catalog | SQLite (discovered items cache) | Free |

## Content Calendar

| Day | Theme |
|-----|-------|
| Mon | Motivational Speech Monday |
| Tue | Throwback Newsreel |
| Wed | Weird Vintage Ads |
| Thu | Classic Cinema Moment |
| Fri | Historical "On This Day" |
| Sat | Educational Film Flashback |
| Sun | "Quote of the Week" compilation |

## Growth Path

| Milestone | Action |
|-----------|--------|
| Launch | 3 Shorts/day across YouTube + TikTok |
| 1K subs | Add themed series playlists |
| 5K subs | Sponsored history/education partnerships |
| 10K subs | Long-form companion videos + community polls |
| 50K subs | Merch, Patreon, licensed educational content |

## Status

Pre-implementation. Design spec complete. See [docs/DESIGN.md](docs/DESIGN.md).

## Related Projects

| Project | Relationship |
|---------|-------------|
| [Animus](https://github.com/AreteDriver/animus) | Parent system |
| [Marketing Engine](https://github.com/AreteDriver/marketing-engine) | Cross-platform posting |

## License

MIT
