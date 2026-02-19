# Story Fire

**AI-powered world folklore YouTube Shorts in the spirit of Jim Henson's The Storyteller.**

An automated content pipeline that brings world folklore and fairy tales to life as YouTube Shorts. Two-character narration (The Storyteller + The Dog), culture-specific AI visuals, and multi-agent orchestration via Gorgon.

---

## Architecture

```
GORGON ORCHESTRATOR ("The Story Fire Engine")

BARD Agent → PAINTER Agent → VOICE Agent → SCRIBE Agent → WEAVER Agent
(Ollama)      (Stable Diff)   (TTS dual)    (Whisper)      (FFmpeg)
     ↓              ↓              ↓              ↓              ↓
  Script JSON    Images/Video   Audio WAV      SRT File       Final MP4

KEEPER Agent (content calendar) → HERALD Agent (YouTube upload)
```

## The Two-Voice System

| Character | Voice Quality |
|-----------|--------------|
| **The Storyteller** | Warm, aged, expressive — confides in the listener |
| **The Dog** | Nasal, matter-of-fact, skeptical — audience surrogate |

## Source Material

3,000+ public domain folk tales from every culture:
- Grimm's Fairy Tales, Aesop's Fables, 1001 Arabian Nights
- Norse Eddas, Japanese Fairy Tales, Russian Folk Tales
- Anansi Stories, Jataka Tales, Kalevala, Mabinogion
- 8+ years of daily content before repeating

## Content Calendar

| Day | Culture Focus |
|-----|--------------|
| Mon | European (Grimm, Slavic) |
| Tue | Asian (Japanese, Chinese, Indian) |
| Wed | African / Caribbean |
| Thu | Norse / Celtic |
| Fri | Arabian / Persian |
| Sat | Greek / Roman / Egyptian |
| Sun | "The Dog Picks" (viewer voted) |

## Tech Stack

| Component | Tool |
|-----------|------|
| LLM | Ollama (Animus) |
| TTS | Piper (free) / ElevenLabs (premium) |
| Visuals | Stable Diffusion (culture-specific styles) |
| Captions | Whisper |
| Assembly | FFmpeg |
| Orchestration | Gorgon |

## Status

Pre-implementation. Design spec complete. See [docs/DESIGN.md](docs/DESIGN.md).

## Related Projects

| Project | Relationship |
|---------|-------------|
| [Animus](https://github.com/AreteDriver/animus) | Parent system |
| [Gorgon](https://github.com/AreteDriver/Gorgon) | Orchestration engine |
| [Marketing Engine](https://github.com/AreteDriver/marketing-engine) | Cross-platform posting |

## License

MIT
