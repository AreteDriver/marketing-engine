# Holmes Wisdom

**AI-powered Science of Mind YouTube Shorts from Ernest Holmes' public domain works.**

An automated content pipeline that transforms Ernest Holmes' pre-1929 public domain writings into YouTube Shorts. Local LLM passage extraction, TTS voiceover, visual generation, and automated assembly.

---

## Architecture

```
Source Text (PD) → Ollama (extract + write hook) → Script JSON
                                                       ↓
                              FFmpeg Assembly ← TTS Voiceover (Piper/ElevenLabs)
                                   ↓                  ↑
                              Final MP4 ← Whisper Captions
                                   ↑
                              Gradient/SD Visuals (mood-matched)
```

## Source Material (Public Domain)

| Title | Year | Status |
|-------|------|--------|
| Creative Mind | 1919 | Public Domain |
| Creative Mind and Success | 1919 | Public Domain |
| The Science of Mind (1st ed.) | 1926 | Public Domain |

The 1938 revised edition is NOT public domain — only the 1926 first edition.

## Monetization

YouTube Shorts are top-of-funnel:
- Free: Shorts (daily) + long-form (weekly)
- Nurture: Email list / Discord community
- Paid: Digital courses, memberships, affiliate links
- Scale: License the pipeline to other creators

## Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| LLM | Ollama | Free |
| TTS | Piper (MVP) / ElevenLabs (upgrade) | Free / ~$5/mo |
| Visuals | Gradient + text overlays (MVP) / Stable Diffusion (v2) | Free |
| Captions | Whisper | Free |
| Assembly | FFmpeg | Free |

## Content Calendar

| Day | Mood |
|-----|------|
| Mon | Empowering affirmation |
| Tue | Deep teaching excerpt |
| Wed | Practical application |
| Thu | Mystical/spiritual insight |
| Fri | Challenge a common belief |
| Sat | Success & abundance |
| Sun | Contemplative meditation prompt |

## Status

Pre-implementation. Design spec complete. See [docs/DESIGN.md](docs/DESIGN.md).

## Related Projects

| Project | Relationship |
|---------|-------------|
| [Animus](https://github.com/AreteDriver/animus) | Parent system |
| [Marketing Engine](https://github.com/AreteDriver/marketing-engine) | Cross-platform posting |

## License

MIT
