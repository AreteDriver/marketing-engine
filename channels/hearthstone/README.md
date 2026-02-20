# Hearthstone — AI Ambient Soundscapes

> Long-form ambient soundscapes (8-12 hours) with subtle motion visuals. AI-generated audio layered with natural recordings. Designed for study, sleep, work, and atmosphere.

## Concept

Themed ambient environments that transport listeners to evocative places:
- "Rainy Bookshop in Edinburgh"
- "Deep Space Station Bridge"
- "Medieval Tavern at Midnight"
- "Japanese Temple in Autumn Rain"
- "Underwater Research Station"
- "Firelit Library in a Thunderstorm"

## Why This Works

| Factor | Advantage |
|--------|-----------|
| **8-12hr watch time** | Massive total watch hours — YouTube algorithm loves this |
| **Evergreen content** | People replay ambient videos hundreds of times |
| **Low production cost** | AI audio + slow-motion/looping visuals |
| **Sleep/study niche** | 100M+ monthly searches for ambient content |
| **Minimal competition edge** | Most ambient channels use the same rain sounds — themed curation is the differentiator |
| **Ad-friendly** | No controversial content, brands love ambient sponsorships |

## Pipeline

```
Theme Config → AI Audio Generation (Suno/Udio/SOUNDRAW)
                    ↓
            Natural Sound Layering (rain, fire, wind, ocean)
                    ↓
            Visual Generation (slow-motion loops, subtle animation)
                    ↓
            FFmpeg Assembly (8-12hr video with seamless audio loops)
                    ↓
            YouTube Upload + Metadata
```

## Content Calendar

| Day | Theme Category |
|-----|---------------|
| Monday | Urban atmosphere (cafes, bookshops, rain on windows) |
| Tuesday | Nature (forests, ocean, mountains, rivers) |
| Wednesday | Fantasy/Sci-fi (space stations, medieval taverns, enchanted libraries) |
| Thursday | Cultural (Japanese gardens, Moroccan courtyards, Irish countryside) |
| Friday | Weather (thunderstorms, snowfall, gentle rain, wind) |
| Saturday | Cozy spaces (fireplace, cabin, train compartment) |
| Sunday | Seasonal special |

## Tech Stack

| Component | Tool | Notes |
|-----------|------|-------|
| Audio generation | Suno / Udio / SOUNDRAW | AI ambient composition |
| Sound layering | FFmpeg / Audacity | Natural sound mixing |
| Visuals | Stable Diffusion / stock video loops | Slow Ken Burns or cinemagraph |
| Assembly | FFmpeg | Seamless loop stitching |
| Upload | YouTube Data API v3 | Scheduled publishing |

## Legal

- AI-generated audio: fully owned
- Natural sounds: royalty-free or self-recorded
- YouTube July 2025 AI policy: disclose AI usage in description
- No static image + AI audio (must have motion visuals)

## Status

Pre-implementation. Directory structure and pipeline scripts scaffolded.
