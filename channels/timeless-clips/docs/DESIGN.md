# Timeless Clips — Public Domain Shorts Factory

## Project Overview

An automated content pipeline that discovers compelling moments from the Internet Archive, Prelinger Archives, NASA, Library of Congress, and other public domain sources, then transforms them into engaging vertical Shorts for YouTube and TikTok. Each Short combines archival footage with original narration, burned-in captions, and period-appropriate visual treatment.

### Why This Works

- **Massive free source library** — millions of public domain videos, films, speeches, and recordings on the Internet Archive alone
- **Evergreen content** — historical moments don't expire, compound interest on views over time
- **Low/no ongoing cost** — all source material is free, local LLM + TTS + FFmpeg
- **Dual platform** — same vertical output works on YouTube Shorts and TikTok
- **Nostalgia + education = viral** — "I never knew this existed" content performs extremely well
- **Defensible** — original narration makes content transformative, not a lazy reupload

### Monetization Strategy

YouTube Shorts and TikTok ad revenue alone won't pay the bills. The Shorts are a **top-of-funnel acquisition engine**:

| Layer | Vehicle | Revenue |
|-------|---------|---------|
| Free | YouTube Shorts (3/day) + TikTok (3/day) | Ad revenue + audience growth |
| Free | YouTube long-form (weekly) | Higher RPM deep dives on topics |
| Nurture | Email list / Discord community | Relationship building |
| Paid | History/culture digital courses | $27-97 one-time |
| Paid | Curated compilation collections | $4.99-9.99 digital |
| Paid | Affiliate links (history books, documentaries, streaming) | Commission |
| Scale | License the pipeline to other history/education creators | SaaS or done-for-you |
| Brand | Sponsored content from educational platforms | $500-5000/video |

---

## Legal Framework

### Public Domain Rules

**US Copyright Basics:**
- Works published before 1929 are public domain in the US — no restrictions
- US Government works (NASA, military, federal agencies) are public domain regardless of date
- Works explicitly dedicated to the public domain (CC0) have no restrictions

**Key Date: January 1, 1929**
- Any film, recording, photograph, or text published before this date is free to use
- This includes: silent films, early talkies, speeches, newsreels, photographs, sheet music
- The public domain expands every January 1 (works from 1929 entered PD on Jan 1, 2025)

### Internet Archive Collections

| Collection | License | Content |
|-----------|---------|---------|
| Prelinger Archives | Public Domain | 60,000+ ephemeral films — ads, PSAs, educational, industrial |
| Feature Films | Mixed (mostly PD) | Classic films, B-movies, silent era masterpieces |
| Community Video | Mixed (check per item) | User-uploaded, often PD or CC |
| Audio Archive | Mixed | Speeches, music, radio broadcasts |
| NASA Images & Video | US Gov PD | Space footage, mission recordings, press conferences |

### Creative Commons Content

| License | Can Use? | Requirements |
|---------|----------|-------------|
| CC0 | Yes | None — equivalent to public domain |
| CC-BY | Yes | Credit the creator |
| CC-BY-SA | Yes | Credit creator + share alike (our Shorts must also be CC-BY-SA) |
| CC-BY-NC | Caution | Non-commercial only — no monetization |
| CC-BY-ND | No | No derivatives — can't remix or add narration |

**Rule**: Only use CC0, CC-BY, or public domain. Avoid CC-NC and CC-ND for monetized content.

### Fair Use Doctrine

For post-1929 material (speeches, news footage, etc.), fair use applies when content is **transformative**:

| Factor | Our Approach |
|--------|-------------|
| Purpose | Educational, commentary, criticism — not entertainment-only |
| Nature | Factual/historical works (favors fair use) |
| Amount | Short clips (30-60s from longer works) |
| Market Effect | Not a substitute for the original |

**How we ensure fair use:**
1. **Original narration** — every clip has our commentary providing context, analysis, or historical significance
2. **Visual treatment** — color grading, text overlays, 9:16 reframing transforms the visual experience
3. **Educational framing** — "Here's why this matters" not just "look at this cool clip"
4. **Short excerpts** — never the full work, only the most compelling 30-60 seconds

### Red Lines (Never Do)

- Never use post-1929 copyrighted material without substantial transformative commentary
- Never reupload raw clips without narration/treatment (that's not transformative)
- Never claim ownership of public domain source material
- Never use CC-NC or CC-ND licensed content for monetized channels
- Never scrape content from paid streaming services
- Never use music that isn't confirmed public domain or CC0
- Always credit sources in video description

### Platform Policies

**YouTube:**
- Content ID may flag public domain content — dispute with documentation
- Keep a record of source URLs and PD status for every clip used
- Add source attribution in description for clean Content ID resolution

**TikTok:**
- Less aggressive copyright enforcement than YouTube
- Same content guidelines apply — educational/commentary framing helps
- Sound detection less sophisticated — narration overlay helps avoid false flags

---

## Source Libraries

### Internet Archive (archive.org)

The primary source for all content. Free API access, massive library.

**Prelinger Archives** — `collection:prelinger`
- 60,000+ "ephemeral" films: advertising, educational, industrial, amateur
- All public domain or CC
- Gold mine for vintage ads, PSAs, safety films, cold war propaganda
- URL: https://archive.org/details/prelinger

**Feature Films** — `collection:feature_films`
- Classic films, silent era, early talkies, B-movies
- Many are public domain (pre-1929 or failed to renew copyright)
- URL: https://archive.org/details/feature_films

**Community Video** — `collection:opensource_movies`
- User-uploaded public domain and CC content
- Mixed quality — need to filter
- URL: https://archive.org/details/opensource_movies

**Audio Archive** — `collection:audio`
- Speeches, radio broadcasts, oral histories
- Great for famous speech Shorts with period visuals
- URL: https://archive.org/details/audio

### NASA Image and Video Library

- All US government works — automatically public domain
- Space footage, mission recordings, astronaut interviews, press conferences
- API: https://images-api.nasa.gov/
- Moon landing, shuttle launches, ISS footage, Mars rovers

### Library of Congress Digital Collections

- Historical photos, films, audio recordings, maps
- Much is public domain or has liberal reuse policies
- URL: https://www.loc.gov/collections/
- Particularly strong for early American history, civil rights, WWII

### LibriVox

- Public domain audiobook recordings read by volunteers
- Great for extracting famous literary quotes with original voice
- All recordings are in the public domain
- URL: https://librivox.org/

### Wikimedia Commons

- PD and CC-licensed images and video
- Strong for historical photographs, portraits, illustrations
- URL: https://commons.wikimedia.org/

---

## Content Categories

### 1. Famous Speeches

**Source**: Archive.org Audio, NASA, LOC, US Gov archives

| Example | Year | Status | Hook |
|---------|------|--------|------|
| FDR "Nothing to fear" | 1933 | PD (US Gov) | "The words that saved a nation from panic" |
| FDR Fireside Chat #1 | 1933 | PD (US Gov) | "The first president to talk directly to your living room" |
| JFK Inaugural | 1961 | PD (US Gov) | "Ask not what your country can do for you..." |
| JFK Moon Speech | 1962 | PD (US Gov) | "We choose to go to the Moon — not because it's easy" |
| NASA Apollo 11 comms | 1969 | PD (US Gov) | "Houston, Tranquility Base here. The Eagle has landed." |
| FDR Declaration of War | 1941 | PD (US Gov) | "A date which will live in infamy" |
| Einstein lecture audio | Pre-1929 | PD | "The voice of the century's greatest mind" |

**Treatment**: Original speech audio + period photographs/footage + text overlay of key quotes + narration providing historical context.

### 2. Classic Film Scenes

**Source**: Archive.org Feature Films, Prelinger

| Example | Year | Status | Hook |
|---------|------|--------|------|
| Nosferatu | 1922 | PD | "The scariest movie ever made — and it's 100 years old" |
| Metropolis | 1927 | PD | "This 1927 film predicted the future of AI" |
| The General (Keaton) | 1926 | PD | "The greatest stunt in cinema history — no CGI, no safety net" |
| A Trip to the Moon | 1902 | PD | "The first sci-fi movie ever made" |
| The Cabinet of Dr. Caligari | 1920 | PD | "The film that invented horror" |
| Safety Last (Lloyd) | 1923 | PD | "He actually hung from that clock — no wires, no green screen" |
| The Phantom of the Opera | 1925 | PD | "The original jump scare" |

**Treatment**: Film clip + subtle color grading + narration explaining historical significance + "Did you know?" facts overlay.

### 3. Vintage Ads & PSAs

**Source**: Prelinger Archives (all PD)

| Example | Era | Hook |
|---------|-----|------|
| Duck and Cover (1951) | Cold War | "This is how kids were told to survive a nuclear bomb" |
| Kitchen of Tomorrow (1956) | 1950s | "1956 predicted your smart kitchen — and got it mostly right" |
| Buster's Last Ride (car safety) | 1960s | "Before seatbelt laws, they made this" |
| Are You Popular? (1947) | 1940s | "1947's guide to being popular is WILD" |
| Design for Dreaming (1956) | 1950s | "GM's vision of the future was insane" |

**Treatment**: Full PD clips — vertical crop, warm vintage color grade, reaction-style narration ("Wait for it..."), text overlays for context.

### 4. Newsreels

**Source**: Archive.org, NASA, LOC, US Gov

| Example | Year | Status | Hook |
|---------|------|--------|------|
| Moon Landing footage | 1969 | PD (NASA) | "The moment humanity left Earth" |
| D-Day newsreel | 1944 | PD (US Gov) | "What the cameras captured on June 6, 1944" |
| Hindenburg disaster | 1937 | PD | "Oh, the humanity — the full uncut footage" |
| Wright Brothers flight | 1903 | PD | "12 seconds that changed the world" |
| Prohibition newsreel | 1920s | PD | "The time America banned alcohol — it went exactly as you'd expect" |

**Treatment**: Historical footage + narration providing context modern audiences need + date/location text overlays + "What happened next" cliffhanger endings.

### 5. Educational Films

**Source**: Prelinger Archives (PD)

| Example | Era | Hook |
|---------|-----|------|
| A is for Atom (1953) | Cold War | "How they explained nuclear energy to kids in 1953" |
| Perversion for Profit (1965) | 1960s | "1965's take on what was destroying America" |
| Dating Do's and Don'ts (1949) | 1940s | "Dating advice from 1949 hits different" |
| Last Date (1950) | 1950s | "The most unhinged driver's ed film ever made" |
| Boys Beware (1961) | 1960s | "The educational film that aged like milk" |

**Treatment**: PD clips with commentary providing modern context — "What they got right," "What aged terribly," "Why this matters." Educational but entertaining framing.

### 6. Quotes with Archival Context

**Source**: LibriVox audio + Archive.org visuals + text overlays

| Quote | Attribution | Visual |
|-------|-----------|--------|
| "The only thing we have to fear is fear itself" | FDR, 1933 | Depression-era footage |
| "That's one small step for man..." | Armstrong, 1969 | Moon landing footage |
| "I have not yet begun to fight" | John Paul Jones | Revolutionary War illustrations |
| "In the middle of difficulty lies opportunity" | Einstein | 1920s physics lab photos |
| "Imagination is more important than knowledge" | Einstein | Chalkboard footage |

**Treatment**: Quote text animates on screen over relevant archival imagery + brief narration on the context and significance + source attribution card.

---

## Pipeline Architecture

```
┌──────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Discover   │────▶│   Download   │────▶│  Extract Moment  │
│  (IA API)    │     │  (cache)     │     │   (Ollama)       │
└──────────────┘     └──────────────┘     └────────┬─────────┘
                                                   │ Script JSON
                                          ┌────────▼─────────┐
                                          │ Generate Narration│
                                          │   (Piper/11Labs)  │
                                          └────────┬─────────┘
                                                   │ WAV audio
                                          ┌────────▼─────────┐
                                          │ Generate Captions │
                                          │    (Whisper)      │
                                          └────────┬─────────┘
                                                   │ SRT file
                                          ┌────────▼─────────┐
                                          │  Compose Short    │
                                          │    (FFmpeg)       │
                                          └────────┬─────────┘
                                                   │
                                              Final MP4
                                           (1080x1920, ≤60s)
```

### Module Descriptions

#### `discover.py` — Content Discovery

Search the Internet Archive and build a local catalog of usable content.

```python
# Internet Archive Advanced Search API
# https://archive.org/advancedsearch.php?q=collection:prelinger&output=json&rows=50

class ContentDiscoverer:
    """Search Internet Archive for public domain video content."""

    def search(self, query: str, collection: str, max_results: int = 50) -> list[ArchiveItem]:
        """Search IA and return matching items with metadata."""

    def filter_usable(self, items: list[ArchiveItem]) -> list[ArchiveItem]:
        """Filter to confirmed PD/CC0/CC-BY items only."""

    def catalog(self, items: list[ArchiveItem]) -> None:
        """Save discovered items to local SQLite catalog."""

    def get_uncatalogued(self, category: str, limit: int = 10) -> list[ArchiveItem]:
        """Return items not yet processed into Shorts."""
```

**ArchiveItem model:**
```python
class ArchiveItem(BaseModel):
    identifier: str          # IA identifier (unique)
    title: str
    description: str
    year: int | None
    collection: str          # prelinger, feature_films, etc.
    media_type: str          # movies, audio, etc.
    license: str             # publicdomain, cc-by, etc.
    source_url: str          # https://archive.org/details/{identifier}
    download_urls: list[str] # Direct file URLs
    duration: float | None   # Seconds
    category: str            # speech, film, ad, newsreel, educational, quote
    tags: list[str]
    discovered_at: datetime
    processed: bool = False
```

#### `download.py` — Media Fetcher

```python
class MediaDownloader:
    """Download and cache media files from Internet Archive."""

    def download(self, item: ArchiveItem, output_dir: Path) -> Path:
        """Download the best available video/audio file."""

    def get_best_file(self, item: ArchiveItem) -> str:
        """Select the best quality file from available formats.
        Prefer: MP4 > OGV > AVI for video, MP3 > OGG for audio."""

    def _rate_limit(self) -> None:
        """Enforce 1 request per second to respect IA servers."""
```

Local cache directory structure:
```
cache/
├── prelinger/
│   ├── DuckAndCover1951/
│   │   ├── metadata.json
│   │   └── DuckAndCover1951.mp4
│   └── DesignForDreaming1956/
│       ├── metadata.json
│       └── DesignForDreaming1956.mp4
├── feature_films/
├── audio/
└── nasa/
```

#### `extract_moment.py` — Moment Extraction (Ollama)

```python
class MomentExtractor:
    """Use Ollama to identify the most compelling 30-60s moment."""

    def extract(self, item: ArchiveItem, transcript: str | None = None) -> ShortScript:
        """Analyze content and produce a script for a Short."""
```

**Ollama prompt strategy:**
```
You are a viral content curator specializing in historical media.

Given this archival content, identify the single most compelling 30-60 second moment
and write a script for a YouTube Short / TikTok.

Content: {title} ({year})
Description: {description}
Category: {category}

Output JSON:
{
    "hook": "Opening line that stops the scroll (< 10 words)",
    "start_time": 45.0,        // Start of the clip in seconds
    "end_time": 90.0,          // End of the clip
    "narration": "Original commentary providing context (2-3 sentences)",
    "text_overlays": [
        {"time": 0.0, "text": "1951", "position": "top-right"},
        {"time": 2.0, "text": "Duck and Cover — Civil Defense Film", "position": "bottom"}
    ],
    "closing": "Call to action or cliffhanger for the next Short",
    "category": "educational",
    "mood": "nostalgic",        // nostalgic, dramatic, funny, eerie, inspiring
    "tags": ["cold war", "1950s", "nuclear", "civil defense"]
}
```

**ShortScript model:**
```python
class ShortScript(BaseModel):
    item_id: str
    hook: str
    start_time: float
    end_time: float
    narration: str
    text_overlays: list[TextOverlay]
    closing: str
    category: str
    mood: str
    tags: list[str]
```

#### `generate_narration.py` — TTS Narration

```python
class NarrationGenerator:
    """Generate TTS voiceover for the narration script."""

    def generate(self, script: ShortScript) -> Path:
        """Generate WAV audio file from script narration."""
```

**Voice requirements:**
- Clear, warm, authoritative narrator voice
- Slightly faster pace for Shorts (engagement)
- Piper TTS (free, local) for MVP
- ElevenLabs (premium) for production quality
- Narration covers: hook + context + closing

#### `generate_captions.py` — Whisper Captions

```python
class CaptionGenerator:
    """Generate burned-in captions using Whisper."""

    def generate(self, audio_path: Path) -> Path:
        """Generate SRT captions from narration audio."""
```

**Caption style:**
- 3-word grouping for readability
- White text with black outline (readable over any background)
- Bottom-center positioning (standard for Shorts)
- Bold for emphasis on key words

#### `compose_short.py` — FFmpeg Assembly

```python
class ShortComposer:
    """Assemble final Short from source clip, narration, captions, and overlays."""

    def compose(self, script: ShortScript, source_path: Path,
                narration_path: Path, caption_path: Path,
                output_path: Path) -> Path:
        """Compose the final 1080x1920 MP4 Short."""
```

**FFmpeg pipeline:**
1. Extract clip segment (start_time → end_time)
2. Crop/pad to 9:16 vertical (1080x1920)
3. Apply color grading filter based on mood
4. Overlay narration audio (mixed with source audio at lower volume)
5. Burn in captions from SRT
6. Add text overlays (year, title, context)
7. Add intro card (0.5s) and outro card (1.5s with CTA)
8. Encode to H.264 MP4, ≤60 seconds

**Color grading presets:**
```python
COLOR_PRESETS = {
    "warm_vintage": "colorbalance=rs=0.1:gs=-0.05:bs=-0.15,curves=vintage",
    "high_contrast_bw": "colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3,eq=contrast=1.3",
    "sepia": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
    "technicolor": "eq=saturation=1.5:contrast=1.1,colorbalance=rs=0.1:bs=-0.1",
    "noir": "colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3,eq=contrast=1.5:brightness=-0.05",
}
```

#### `pipeline.py` — Orchestrator

```python
class TimelessClipsPipeline:
    """Full pipeline: discover → download → extract → narrate → caption → compose."""

    def run(self, category: str = "all", batch_size: int = 5) -> list[Path]:
        """Run the full pipeline for a batch of Shorts."""

    def run_single(self, identifier: str) -> Path:
        """Process a single IA item into a Short."""
```

**CLI interface:**
```bash
timeless-clips discover --collection prelinger --category ads --limit 50
timeless-clips process --category ads --batch 5
timeless-clips process --identifier DuckAndCover1951
timeless-clips catalog --status         # Show catalog stats
timeless-clips export --week 2025-03-03 # Export to marketing-engine
```

---

## Visual Treatment

### 9:16 Vertical Reframing

Most archival footage is 4:3 or wider. Strategies for vertical:

| Strategy | When to Use |
|----------|------------|
| Center crop | Talking head / single subject |
| Letterbox + blur fill | Wide shots where cropping loses context |
| Pan & scan (Ken Burns) | Still images or slow scenes |
| Split frame | Quote text top + footage bottom |
| Full frame + context bar | Small footage with large text overlay area |

### Text Overlay System

```
┌────────────────────────┐
│  ┌──────────────────┐  │
│  │    HOOK TEXT      │  │  ← First 2 seconds (bold, large)
│  └──────────────────┘  │
│                        │
│                        │
│    [Archival footage   │
│     with color grade]  │
│                        │
│                        │
│  ┌──────────────────┐  │
│  │  Context bar:     │  │  ← Persistent bottom bar
│  │  "1951 • Civil    │  │
│  │   Defense Film"   │  │
│  └──────────────────┘  │
│  ┌──────────────────┐  │
│  │  CAPTION TEXT     │  │  ← Narration captions
│  └──────────────────┘  │
└────────────────────────┘
```

### Intro/Outro Cards

**Intro (0.5s):**
- Channel logo/name fade in
- Category icon (film reel, microphone, etc.)

**Outro (1.5s):**
- "Follow for more" CTA
- Next Short teaser text
- Channel handle

---

## Internet Archive API Integration

### Advanced Search

```
GET https://archive.org/advancedsearch.php
?q=collection:prelinger AND mediatype:movies AND year:[1940 TO 1960]
&fl[]=identifier,title,description,year,licenseurl,collection
&sort[]=downloads desc
&rows=50
&output=json
```

**Useful query patterns:**
```python
QUERIES = {
    "prelinger_ads": "collection:prelinger AND subject:advertising",
    "prelinger_educational": "collection:prelinger AND subject:educational",
    "silent_films": "collection:feature_films AND year:[1895 TO 1928]",
    "speeches": "collection:audio AND subject:speeches AND mediatype:audio",
    "nasa_video": "collection:nasa AND mediatype:movies",
    "newsreels": "collection:newsandpublicaffairs AND mediatype:movies",
}
```

### Metadata Endpoint

```
GET https://archive.org/metadata/{identifier}
```

Returns full item metadata including all available files, formats, sizes.

### Download

```
GET https://archive.org/download/{identifier}/{filename}
```

**Rate limiting**: 1 request per second minimum. Use `time.sleep(1)` between requests. Respect `robots.txt`. Cache everything locally.

### Local Catalog (SQLite)

```sql
CREATE TABLE catalog (
    identifier TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    year INTEGER,
    collection TEXT NOT NULL,
    license TEXT,
    category TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',    -- JSON array
    duration REAL,
    source_url TEXT NOT NULL,
    download_url TEXT,
    local_path TEXT,                     -- Path to cached file
    processed BOOLEAN DEFAULT FALSE,
    processed_at TEXT,
    short_path TEXT,                     -- Path to output Short
    discovered_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'  -- Full IA metadata JSON
);
CREATE INDEX idx_catalog_category ON catalog(category);
CREATE INDEX idx_catalog_processed ON catalog(processed);
CREATE INDEX idx_catalog_collection ON catalog(collection);
```

---

## Content Calendar

| Day | Theme | Source Focus | Mood |
|-----|-------|-------------|------|
| Monday | Motivational Speech Monday | Speeches, quotes | Inspiring |
| Tuesday | Throwback Newsreel | Newsreels, historical events | Dramatic |
| Wednesday | Weird Vintage Ads | Prelinger ads, PSAs | Funny/nostalgic |
| Thursday | Classic Cinema Moment | Silent films, early talkies | Cinematic |
| Friday | Historical "On This Day" | Events matching today's date | Educational |
| Saturday | Educational Film Flashback | Classroom films, safety | Nostalgic/funny |
| Sunday | Quote of the Week | Famous quotes + archival visuals | Reflective |

**Volume target**: 3 Shorts per day (21/week) across both platforms.

---

## Metadata & SEO

### YouTube Shorts

**Title patterns:**
- `"This {year} {type} is WILD 😳 #shorts #history"`
- `"{Famous quote}" — {Person}, {Year} #shorts`
- `"They actually showed THIS to kids in {year} #shorts"`
- `"The moment that changed everything — {date} #shorts"`

**Description template:**
```
{Hook sentence}

This clip is from "{original_title}" ({year}), sourced from the {collection}
on the Internet Archive ({source_url}).

{2-3 sentences of context}

🎬 Source: {source_url}
📜 License: Public Domain / {license}

#history #vintage #shorts #timelessclips #{category} #{decade}
```

**Hashtag strategy:** Max 3-5 per Short. Mix evergreen (#history, #vintage) with category-specific (#coldwar, #silentfilm).

### TikTok

**Title patterns:**
- Same as YouTube but shorter
- More emoji-driven
- Trending sound reference if applicable

**Hashtag strategy:** Up to 5 hashtags. Include #fyp, #history, plus 2-3 specific.

---

## Monetization

### Revenue Streams

| Stream | Requirements | Estimated Revenue |
|--------|-------------|-------------------|
| YouTube Shorts Fund | 1K subs + 10M Short views/90 days | $100-500/mo at scale |
| YouTube Partner (long-form) | 1K subs + 4K watch hours | Higher RPM on compilations |
| TikTok Creator Fund | 10K followers + 100K views/30 days | $20-100/mo |
| Affiliate | Amazon history books, documentary streaming | 5-10% commission |
| Sponsored content | Educational platforms, history channels | $500-5000/video |
| Digital products | Curated clip compilations, educational packs | $4.99-19.99 |

### Unit Economics

- **Cost per Short**: ~$0 (all free local tools) or ~$0.10 with ElevenLabs TTS
- **Time per Short**: ~5 min automated, ~2 min human review
- **Break-even**: First dollar of ad revenue (effectively zero cost basis)

---

## Growth Path

| Milestone | Timeline | Actions |
|-----------|----------|---------|
| Launch | Week 1 | 21 Shorts queued, daily posting begins |
| 100 subs | Month 1 | Analyze which categories perform best, double down |
| 1K subs | Month 2-3 | Add themed playlists, community tab engagement |
| 5K subs | Month 4-6 | Weekly long-form compilations, sponsor outreach |
| 10K subs | Month 6-9 | Merch, Patreon, educational partnerships |
| 50K subs | Year 1-2 | Multiple daily uploads, series format, brand deals |

---

## Configuration

```yaml
# config.yaml — Timeless Clips Pipeline Configuration

# Internet Archive settings
archive:
  base_url: "https://archive.org"
  rate_limit_seconds: 1.0
  cache_dir: "cache/"
  preferred_formats: ["mp4", "ogv", "avi"]

# LLM settings
llm:
  provider: "ollama"
  model: "llama3.2"
  host: "http://localhost:11434"

# TTS settings
tts:
  engine: "piper"  # piper | elevenlabs
  voice: "en_US-lessac-medium"
  # elevenlabs_api_key: ""  # Set via ELEVENLABS_API_KEY env var
  # elevenlabs_voice_id: ""

# Whisper settings
captions:
  model: "base"  # tiny | base | small | medium | large
  language: "en"
  word_grouping: 3
  style: "white_outline"

# Output settings
output:
  resolution: "1080x1920"
  max_duration: 60
  format: "mp4"
  codec: "libx264"
  crf: 23
  output_dir: "output/"

# Visual treatment
visuals:
  default_color_preset: "warm_vintage"
  add_intro_card: true
  intro_duration: 0.5
  add_outro_card: true
  outro_duration: 1.5
  context_bar: true

# Content calendar
calendar:
  timezone: "America/New_York"
  daily_target: 3
  themes:
    monday: "speech"
    tuesday: "newsreel"
    wednesday: "ad"
    thursday: "film"
    friday: "on_this_day"
    saturday: "educational"
    sunday: "quote"

# Catalog database
catalog:
  db_path: "catalog.db"
```

---

## Future Enhancements

### Phase 2 — Auto-Upload
- YouTube Data API v3 for automated Short publishing
- TikTok Publishing API for cross-posting
- Scheduled uploads matching content calendar
- Integration with marketing-engine approval queue

### Phase 3 — Intelligence
- A/B testing thumbnails (text overlay variations)
- Analytics feedback loop (which categories/moods perform best)
- Auto-adjust content calendar based on performance data
- Trending topic detection (match historical content to current events)

### Phase 4 — Series & Long-Form
- Themed series playlists ("Cold War Wednesdays", "Silent Film Saturdays")
- Weekly long-form compilations (10-15 min) for higher RPM
- Community polls for "What should we feature next?"
- Podcast version of narration tracks

### Phase 5 — Scale
- Multi-channel: spin off successful categories into dedicated channels
- Pipeline licensing: sell the tool to other history/education creators
- Educational partnerships: schools, museums, libraries
- Collaborative: community-submitted clips with attribution
