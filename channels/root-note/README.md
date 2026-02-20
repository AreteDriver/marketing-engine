# Root Note — Forgotten Instruments of the World

> YouTube Shorts spotlighting rare, forgotten, and culturally significant instruments from around the world. AI-composed demonstrations + cultural context narration.

## Concept

Each Short introduces a rare or forgotten instrument:
- **What it sounds like** (AI-composed or sampled demonstration)
- **Where it comes from** (cultural and historical context)
- **Why it matters** (what makes it unique)

Featured instruments: hurdy-gurdy, kora, oud, erhu, didgeridoo, shamisen, balalaika, sitar, gamelan, mbira, nyckelharpa, hang drum, theremin, glass armonica, ondes Martenot, daxophone, waterphone, and hundreds more.

## Why This Works

| Factor | Advantage |
|--------|-----------|
| **Unique niche** | Nobody owns "rare instruments" on Shorts |
| **Visual hook** | Unusual instruments are scroll-stoppers |
| **Educational** | YouTube favors educational content in algorithm |
| **Cultural depth** | Each instrument connects to a living culture |
| **Infinite content** | 1000+ instruments across world cultures |
| **Cross-promotion** | Pairs naturally with Story Fire (same cultures) |

## Pipeline

```
Instrument Research → Script Generation (Ollama)
                          ↓
                   AI Audio Demo (Suno/sample library)
                          ↓
                   Visual Generation (instrument images + cultural context)
                          ↓
                   Narration TTS (warm, knowledgeable voice)
                          ↓
                   Caption Generation (Whisper)
                          ↓
                   FFmpeg Assembly (40-60s Short)
                          ↓
                   YouTube Upload + Metadata
```

## Content Calendar

| Day | Region/Category |
|-----|----------------|
| Monday | European (hurdy-gurdy, nyckelharpa, glass armonica) |
| Tuesday | African (kora, mbira, talking drum, balafon) |
| Wednesday | Asian (erhu, shamisen, gamelan, pipa) |
| Thursday | Middle Eastern (oud, ney, qanun, santoor) |
| Friday | Americas (charango, berimbau, steel pan, quena) |
| Saturday | Experimental/Modern (theremin, hang drum, waterphone) |
| Sunday | "Battle" — two instruments from different cultures compared |

## Script Format

```json
{
    "instrument": "Hurdy-gurdy",
    "region": "Medieval Europe",
    "hook": "This instrument was banned from churches for being too beautiful.",
    "description": "A mechanical string instrument where a rosined wheel acts as a bow...",
    "cultural_context": "Troubadours carried these across medieval France...",
    "sound_description": "A droning, buzzing hum beneath a sweet melody — like a violin having a conversation with a bagpipe.",
    "fun_fact": "Led Zeppelin used one on 'In Through the Out Door'.",
    "mood": "mystical",
    "estimated_duration_seconds": 50
}
```

## Tech Stack

| Component | Tool | Notes |
|-----------|------|-------|
| Research | Ollama / Claude | Instrument history and context |
| Audio demo | Suno / sample libraries | AI-composed demonstrations |
| Visuals | Stable Diffusion / stock | Instrument imagery + cultural scenes |
| Narration | Piper / ElevenLabs | Warm, knowledgeable narrator |
| Captions | Whisper | Word-level for Shorts engagement |
| Assembly | FFmpeg | 1080x1920 vertical Short |
| Upload | YouTube Data API v3 | Scheduled publishing |

## Legal

- AI-generated audio: fully owned
- Instrument facts: public knowledge
- YouTube AI policy: disclose in description
- Cultural sensitivity: respectful, educational framing

## Status

Pre-implementation. Directory structure and pipeline scripts scaffolded.
