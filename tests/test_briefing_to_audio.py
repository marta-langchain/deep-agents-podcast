"""Tests for the ElevenLabs briefing → audio flow.

Maps to the PR test plan:
1. ELEVENLABS_API_KEY is required (and placeholders are rejected)
2. save_briefing() writes markdown under output/
3. briefing_to_audio() writes an MP3 under output/ (ElevenLabs mocked)
4. .env secrets / generated artifacts stay out of git via .gitignore
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from utils.briefing_to_audio import (
    OUTPUT_DIR,
    ROOT,
    briefing_to_audio,
    markdown_to_speech_text,
)
from utils.viz import save_briefing


@pytest.fixture()
def tmp_repo(tmp_path, monkeypatch):
    """Point OUTPUT_DIR / agent paths at an isolated temp tree."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()

    monkeypatch.setattr("utils.briefing_to_audio.OUTPUT_DIR", output_dir)
    monkeypatch.setattr("utils.briefing_to_audio.ROOT", tmp_path)
    monkeypatch.setattr("utils.viz.OUTPUT_DIR", output_dir)
    return tmp_path, output_dir, agent_dir


def test_api_key_required(tmp_repo, monkeypatch):
    """Test plan: ELEVENLABS_API_KEY must be set (not missing / placeholder)."""
    _, output_dir, _ = tmp_repo
    briefing = output_dir / "episode_2_briefing.md"
    briefing.write_text("# Episode 2\n\nHello world.\n", encoding="utf-8")

    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
        briefing_to_audio(briefing, api_key=None)

    with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
        briefing_to_audio(briefing, api_key="<elevenlabs-api-key>")


def test_save_briefing_writes_under_output(tmp_repo):
    """Test plan: save_briefing(...) writes markdown under output/."""
    _, output_dir, agent_dir = tmp_repo
    src = agent_dir / "briefing.md"
    src.write_text("# Episode 2\n\nBody text.\n", encoding="utf-8")

    save_briefing(src=src, dst="episode_2_briefing.md")

    dest = output_dir / "episode_2_briefing.md"
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")
    assert dest.parent == output_dir


def test_briefing_to_audio_writes_mp3_under_output(tmp_repo):
    """Test plan: synthesize episode_2_briefing.md → output/episode_2_briefing.mp3."""
    _, output_dir, _ = tmp_repo
    briefing = output_dir / "episode_2_briefing.md"
    briefing.write_text(
        "# Episode 2\n\nIn our *inaugural* episode, we explored clocks.\n",
        encoding="utf-8",
    )

    fake_audio = [b"ID3", b"fake-mp3-bytes"]

    with patch("utils.briefing_to_audio.ElevenLabs") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = iter(fake_audio)
        mock_client_cls.return_value = mock_client

        out = briefing_to_audio(
            "episode_2_briefing.md",
            api_key="test-key-not-a-placeholder",
        )

    assert out == output_dir / "episode_2_briefing.mp3"
    assert out.exists()
    assert out.read_bytes() == b"".join(fake_audio)
    mock_client.text_to_speech.convert.assert_called_once()
    call_kwargs = mock_client.text_to_speech.convert.call_args.kwargs
    assert "inaugural" in call_kwargs["text"]
    assert "*" not in call_kwargs["text"]
    assert call_kwargs["voice_id"] == "6fZce9LFNG3iEITDfqZZ"


def test_gitignore_keeps_secrets_and_artifacts_out_of_git():
    """Test plan: .env secrets and generated output are gitignored."""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore
    assert "output/" in gitignore
    assert "episode_*_briefing.md" in gitignore
    assert "episode_*_briefing.mp3" in gitignore

    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "ELEVENLABS_API_KEY=" in env_example
    assert "<elevenlabs-api-key>" in env_example
    # Never commit a real-looking key in the example file.
    assert "ELEVENLABS_API_KEY=\"<" in env_example or 'ELEVENLABS_API_KEY="<' in env_example


def test_markdown_to_speech_strips_markup():
    text = markdown_to_speech_text("# Title\n\nHello **world** and *italics*.\n")
    assert text.startswith("Title")
    assert "**" not in text
    assert "*" not in text
    assert "Hello world and italics." in text
