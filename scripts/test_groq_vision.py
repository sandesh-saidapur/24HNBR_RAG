"""Try a Groq vision model on a few slideshow photos and print what it reads.

Usage (from the project root, on your own computer):
    python scripts/test_groq_vision.py                 # list vision-capable models
    python scripts/test_groq_vision.py MODEL_ID        # ask the model about 3 photos
The key is read from GROQ_API_KEY or from .env; it is never printed.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.groq.com/openai/v1"
HINTS = ("vision", "llama-4", "scout", "maverick", "qwen", "-vl", "vl-")
PROMPT = (
    "This is a photo from the 24 Hours of Nürburgring. If a race car number is clearly "
    "visible on the car, reply with that number only. Otherwise reply NONE."
)


def key() -> str:
    if os.environ.get("GROQ_API_KEY"):
        return os.environ["GROQ_API_KEY"]
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("GROQ_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("GROQ_API_KEY not found")


def call(path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        API + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json",
                 "User-Agent": "trackside24"},
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def photos(n: int = 3) -> list[Path]:
    """Spread the sample across the slideshow, so track-side shots are included."""
    files = [f for f in sorted((ROOT / "frontend/public/slideshow").glob("*.jpg")) if not f.name.startswith("_")]
    step = max(1, len(files) // n)
    return files[::step][:n]


def call_retry(path: str, body: dict) -> dict:
    """Groq's free tier rate-limits requests; wait and retry instead of failing."""
    for attempt in range(5):
        try:
            return call(path, body)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            time.sleep(15 * (attempt + 1))
    raise RuntimeError("unreachable")


def main() -> None:
    if len(sys.argv) == 1:
        ids = sorted(m["id"] for m in call("/models")["data"])
        print("vision-capable candidates:")
        for model in ids:
            if any(h in model.lower() for h in HINTS):
                print("  ", model)
        return
    model = sys.argv[1]
    for photo in photos():
        image = base64.b64encode(photo.read_bytes()).decode()
        body = {
            "model": model,
            "max_tokens": 30,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}},
                ],
            }],
        }
        reply = call_retry("/chat/completions", body)["choices"][0]["message"]["content"]
        print(f"{photo.name}: {reply.strip()}")
        time.sleep(5)


if __name__ == "__main__":
    main()
