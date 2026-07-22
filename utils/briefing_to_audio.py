"""Convert an episode briefing markdown file to speech via ElevenLabs TTS."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
DEFAULT_VOICE_ID = "6fZce9LFNG3iEITDfqZZ"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_INPUT = OUTPUT_DIR / "episode_2_briefing.md"
DEFAULT_OUTPUT = OUTPUT_DIR / "episode_2_briefing.mp3"


def load_env() -> None:
    load_dotenv(dotenv_path=ROOT / ".env", override=True)


def markdown_to_speech_text(markdown: str) -> str:
    """Strip light markdown so TTS reads clean prose."""
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _resolve_path(path: str | Path, *, default_dir: Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    # Prefer paths already rooted under output/ or other explicit dirs.
    if path.parts and path.parts[0] in {"output", "agent"}:
        return ROOT / path
    return default_dir / path


def synthesize(
    text: str,
    *,
    api_key: str,
    voice_id: str,
    model_id: str,
    output_path: Path,
) -> None:
    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format="mp3_44100_128",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        for chunk in audio:
            if chunk:
                f.write(chunk)


def briefing_to_audio(
    input_path: str | Path = DEFAULT_INPUT,
    output_path: str | Path | None = None,
    *,
    voice_id: str = DEFAULT_VOICE_ID,
    model_id: str = DEFAULT_MODEL_ID,
    api_key: str | None = None,
) -> Path:
    """Convert a briefing markdown file to an MP3 under ``output/``."""
    load_env()
    key = (api_key or os.getenv("ELEVENLABS_API_KEY", "")).strip()
    if not key or key.startswith("<"):
        raise ValueError(
            "ELEVENLABS_API_KEY is missing. Add it to .env "
            "(https://elevenlabs.io/app/settings/api-keys)."
        )

    in_path = _resolve_path(input_path, default_dir=OUTPUT_DIR)
    if output_path is None:
        out_path = OUTPUT_DIR / f"{in_path.stem}.mp3"
    else:
        out_path = _resolve_path(output_path, default_dir=OUTPUT_DIR)

    if not in_path.exists():
        raise FileNotFoundError(f"Input not found: {in_path}")

    speech_text = markdown_to_speech_text(in_path.read_text(encoding="utf-8"))
    if not speech_text:
        raise ValueError(f"No text to synthesize in {in_path}")

    print(f"Synthesizing {len(speech_text)} chars from {in_path} …")
    synthesize(
        speech_text,
        api_key=key,
        voice_id=voice_id or os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID),
        model_id=model_id or os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID),
        output_path=out_path,
    )
    print(f"Wrote {out_path}")
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert an episode briefing markdown file to MP3 with ElevenLabs.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Markdown briefing path (default: {DEFAULT_INPUT.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Output MP3 path (default: {DEFAULT_OUTPUT.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--voice-id",
        default=os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID),
        help=f"ElevenLabs voice id (default: {DEFAULT_VOICE_ID})",
    )
    parser.add_argument(
        "--model-id",
        default=os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID),
        help=f"ElevenLabs model id (default: {DEFAULT_MODEL_ID})",
    )
    return parser.parse_args()


def main() -> int:
    load_env()
    args = parse_args()
    try:
        briefing_to_audio(
            input_path=args.input,
            output_path=args.output,
            voice_id=args.voice_id,
            model_id=args.model_id,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
