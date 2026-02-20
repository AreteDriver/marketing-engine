#!/usr/bin/env python3
"""
BARD Agent — Extract dramatic moments from folk tales via Ollama.
Writes Storyteller + Dog scripts in the spirit of Jim Henson's The Storyteller.

Usage:
    python scripts/extract_tale.py <source_file> <culture>
    python scripts/extract_tale.py sources/grimm_hansel_gretel.txt european
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """You are The Storyteller — an ancient, warm, slightly mischievous keeper \
of tales from every corner of the world. You sit by a crackling fire, \
a skeptical but lovable Dog at your feet, and you tell stories the way \
they were meant to be told: out loud, by the fire, with the shadows \
dancing on the walls.

YOUR VOICE:
- You CONFIDE in the listener. You lean in. You whisper the scary parts \
  and beam through the wonderful parts.
- You use the oral tradition: rhythmic repetitions, run-on momentum, \
  direct address. "And he walked and he walked and he walked..."
- You are occasionally surprised by your own story: "And THEN — oh, \
  now this is the part — then she..."
- You find dark things wryly amusing, not horrifying. A witch eating \
  children gets a raised eyebrow, not a scream.
- You love these stories. Every one. You've told them a hundred times \
  and they still delight you.
- You speak in short, punchy sentences mixed with long, rolling ones. \
  Rhythm matters. Sound matters. These words are meant to be HEARD.
- You never explain a moral. The story IS the moral. Trust the listener.

THE DOG (optional interjections):
- Skeptical: "That doesn't sound right."
- Frightened: "I don't like this bit. Skip ahead."
- Impatient: "But did it END well?"
- Loyal: "Tell it again."
- The Dog's voice is distinct — shorter sentences, blunter, more modern. \
  A counterweight to the Storyteller's lyricism.

WHAT YOU NEVER DO:
- Never sound like a documentary narrator
- Never explain or moralize — the story speaks for itself
- Never use modern slang (the Dog can, sparingly)
- Never rush — pauses are part of the music
- Never make it safe or sanitized — these are REAL folk tales with \
  real teeth. Darkness is part of the deal.
- Never reference the source culture academically

FOR YOUTUBE SHORTS (40-55 seconds):
- Open with a hook that creates an OPEN LOOP
- The hook should feel like catching the Storyteller mid-tale
- Build to a single dramatic peak or revelation
- End with a satisfying closing, cliffhanger, or Storyteller aside
- 100-140 spoken words total

Respond ONLY in this JSON format:
{
    "hook": "The Storyteller's opening — mid-thought, conspiratorial, an open loop",
    "dog_reaction": "The Dog's response to the hook (or null if not used)",
    "narration": "The core tale with [pause] and [whisper] / [louder] vocal cues",
    "dog_interjection": "Optional mid-story Dog comment (or null)",
    "closing": "The Storyteller's closing — satisfying, wry, or haunting",
    "dog_closing": "Dog's final word (or null) — often the punchline",
    "tale_title": "The name of the folk tale",
    "culture": "Origin culture/region",
    "themes": ["theme1", "theme2", "theme3"],
    "visual_cues": ["specific scene descriptions for image generation"],
    "mood": "warm_dark|whimsical|haunting|triumphant|bittersweet|terrifying_but_wry",
    "palette": "firelit_gold|moonlit_blue|forest_green|desert_amber|frost_silver",
    "estimated_duration_seconds": 48,
    "word_count": 125,
    "has_dog": true
}"""

# Culture-specific prompt additions
CULTURE_PROMPTS = {
    "european": (
        "You are telling tales from the old countries — Germany, Russia, Ireland, "
        "Scandinavia, the Balkans. Stone castles and dark forests. Witches in "
        "the woods and kings with terrible secrets."
    ),
    "japanese": (
        "Tonight, the tales come from far across the sea — from the land of "
        "mist and mountains, where the spirits wear a thousand faces. Fox "
        "women and snow ghosts and temples where the dead still pray."
    ),
    "african": (
        "Ah, NOW we go to where the stories began. Where Anansi the Spider — "
        "clever, terrible, wonderful Anansi — tricked even the Sky God himself. "
        "These are stories that beat like a drum and laugh like a river."
    ),
    "norse": (
        "The fire burns low and the wind howls. Good. These are stories for "
        "dark nights. Stories of gods who knew they would die, and fought "
        "anyway. Of a world built on a giant's bones."
    ),
    "arabian": (
        "Close your eyes. Smell the spices? Hear the fountain? We are in the "
        "palace of a thousand and one nights, where a woman saved her own life "
        "by never, ever finishing the story."
    ),
    "celtic": (
        "The mist rolls in from the sea, and the stones remember. These tales "
        "come from the green and ancient lands where the Fair Folk walk between "
        "worlds, and a careless word can bind you for a hundred years."
    ),
    "greek": (
        "The wine is poured, the fire is hot, and the gods are listening. "
        "These are the tales they told in marble halls and olive groves — "
        "tales of heroes who dared too much and gods who forgave too little."
    ),
    "indian": (
        "Come, sit. The tales tonight are older than old — from a land of "
        "ten thousand gods and talking animals wiser than any king. Tales "
        "within tales within tales, like a jewelled box that never empties."
    ),
}

USER_PROMPT_TEMPLATE = """Here is a folk tale from the {culture} tradition. \
Extract the most dramatic moment and create a Storyteller YouTube Short script.

---
{source_text}
---

Remember: JSON only. Hook must create an open loop. 100-140 spoken words. \
Include Dog reactions where they add pacing or humor."""

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "scripts"


def extract_tale(source_text: str, culture: str) -> dict:
    """Send tale to Ollama and get Storyteller script back."""
    culture_addition = CULTURE_PROMPTS.get(culture, CULTURE_PROMPTS["european"])
    full_system = f"{SYSTEM_PROMPT}\n\n{culture_addition}"

    payload = {
        "model": MODEL,
        "prompt": USER_PROMPT_TEMPLATE.format(
            culture=culture,
            source_text=source_text,
        ),
        "system": full_system,
        "stream": False,
        "options": {
            "temperature": 0.8,
            "top_p": 0.9,
        },
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()

    raw = response.json()["response"]

    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]

    return json.loads(raw.strip())


def process_sources(sources_dir: str, culture: str) -> None:
    """Process all source tale files."""
    sources_path = Path(sources_dir)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for source_file in sorted(sources_path.glob("*.txt")):
        print(f"[->] Processing: {source_file.name}")
        source_text = source_file.read_text()

        try:
            script = extract_tale(source_text, culture)
            out_file = OUTPUT_DIR / f"{source_file.stem}_script.json"
            out_file.write_text(json.dumps(script, indent=2))
            print(f"  [+] Script: {out_file.name}")
            print(f"      Tale: {script.get('tale_title', '?')}")
            print(f"      Hook: {script['hook'][:60]}...")
            print(f"      Mood: {script.get('mood', '?')} | Dog: {script.get('has_dog', False)}")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  [x] Failed to parse: {e}")
        except requests.RequestException as e:
            print(f"  [x] Ollama error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_tale.py <sources_dir> <culture>")
        print(f"Cultures: {', '.join(CULTURE_PROMPTS.keys())}")
        sys.exit(1)

    process_sources(sys.argv[1], sys.argv[2])
