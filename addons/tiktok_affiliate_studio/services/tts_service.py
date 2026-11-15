"""Local Vietnamese TTS via ZeroTTS.

Install:
  pip install zerotts

First run downloads ~900MB weights from HuggingFace (cached under HF_HOME).

Env:
  TTS_MODEL=zeroweight-ai/ZeroTTS
  TTS_VOICE=maichi
  TTS_SENTENCE_PAUSE_MS=200
  TTS_SAMPLE_RATE=48000
"""
from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

_logger = logging.getLogger(__name__)

_ENGINE = None


def _fix_onnx_symlinks(model_dir: Path) -> None:
    """ONNXRuntime 1.18+ forbids external data files when symlinks resolve to different blob dirs.
    Replace symlinks with real files in onnx/ to satisfy ONNXRuntime external data path validation.
    """
    onnx_dir = model_dir / "onnx"
    if not onnx_dir.exists():
        return
    for p in onnx_dir.rglob("*"):
        if p.is_symlink():
            try:
                target = p.resolve()
                if target.exists() and target.is_file():
                    p.unlink()
                    shutil.copyfile(target, p)
            except Exception as exc:
                _logger.warning("Could not materialize symlink %s: %s", p, exc)


def _patch_path_read_text_utf8() -> None:
    """ZeroTTS uses Path.read_text() without encoding; Windows defaults to cp1252."""
    if getattr(Path.read_text, "_video_worker_utf8", False):
        return
    _orig = Path.read_text

    def _read_text(self, encoding=None, errors=None):  # noqa: ANN001
        return _orig(self, encoding=encoding or "utf-8", errors=errors)

    _read_text._video_worker_utf8 = True  # type: ignore[attr-defined]
    Path.read_text = _read_text  # type: ignore[method-assign]


# Apply ASAP so any ZeroTTS call (including after worker reload) uses UTF-8.
_patch_path_read_text_utf8()


class TTSError(Exception):
    """Raised when TTS synthesis fails."""

    def __init__(self, message: str, *, scene_id: int | None = None, scene_sequence: int | None = None):
        self.scene_id = scene_id
        self.scene_sequence = scene_sequence
        prefix = ""
        if scene_id is not None:
            prefix = f"scene_id={scene_id}"
            if scene_sequence is not None:
                prefix += f" seq={scene_sequence}"
            prefix += ": "
        elif scene_sequence is not None:
            prefix = f"scene seq={scene_sequence}: "
        super().__init__(prefix + message)


def _sentence_pause_seconds() -> float:
    try:
        ms = float(os.getenv("TTS_SENTENCE_PAUSE_MS", "200"))
    except ValueError:
        ms = 200.0
    return max(0.0, ms / 1000.0)


def get_tts_engine():
    """Lazy-load ZeroTTS singleton."""
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    _patch_path_read_text_utf8()
    model_id = os.getenv("TTS_MODEL", "zeroweight-ai/ZeroTTS")
    _logger.info("Loading ZeroTTS model %s (first time may download ~900MB)...", model_id)
    try:
        from zerotts import ZeroTTS
        from zerotts.hub import resolve_model_dir
    except ImportError as exc:
        raise TTSError(
            "zerotts is not installed. Run: pip install zerotts"
        ) from exc

    try:
        model_dir = resolve_model_dir(model_id)
        _fix_onnx_symlinks(model_dir)
        engine = ZeroTTS(model_dir)
        # Optional warmup keeps first scene faster.
        if os.getenv("TTS_WARMUP", "1").lower() in ("1", "true", "yes"):
            try:
                engine.warmup()
            except Exception:
                _logger.warning("ZeroTTS warmup failed; continuing without warmup", exc_info=True)
        _ENGINE = engine
        voices = []
        try:
            voices = list(engine.list_voices() or [])
        except Exception:
            pass
        _logger.info("ZeroTTS ready. voices=%s", voices[:10] if voices else "(unknown)")
        return _ENGINE
    except Exception as exc:
        raise TTSError(f"Failed to load ZeroTTS model: {exc}") from exc


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[\.!\?…])\s+", text.strip())
    return [p.strip() for p in parts if p and p.strip()]


def _audio_duration_seconds(path: Path) -> float:
    info = sf.info(str(path))
    if info.frames <= 0 or info.samplerate <= 0:
        raise TTSError(f"Invalid audio file: {path}")
    return float(info.frames) / float(info.samplerate)


def synthesize_to_wav(
    text: str,
    dest_path: Path,
    *,
    voice: str | None = None,
    scene_id: int | None = None,
    scene_sequence: int | None = None,
) -> dict[str, Any]:
    """Synthesize Vietnamese narration to a WAV file and return metadata."""
    narration = (text or "").strip()
    if not narration:
        raise TTSError(
            "narration is empty",
            scene_id=scene_id,
            scene_sequence=scene_sequence,
        )

    voice_name = voice or os.getenv("TTS_VOICE", "maichi")
    pause = _sentence_pause_seconds()
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        engine = get_tts_engine()
        sample_rate = int(getattr(engine, "sample_rate", 0) or os.getenv("TTS_SAMPLE_RATE", "48000"))
        sentences = _split_sentences(narration) or [narration]
        chunks: list[np.ndarray] = []

        for index, sentence in enumerate(sentences):
            audio = engine.synthesize(sentence, voice=voice_name)
            # ZeroTTS may return (1, n) or (n,) float32
            arr = np.asarray(audio, dtype=np.float32)
            if arr.ndim == 2:
                arr = arr.reshape(-1)
            chunks.append(arr)
            if pause > 0 and index < len(sentences) - 1:
                chunks.append(np.zeros(int(sample_rate * pause), dtype=np.float32))

        combined = np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
        # Peak normalize lightly to avoid clipping
        peak = float(np.max(np.abs(combined))) if combined.size else 0.0
        if peak > 1.0:
            combined = combined / peak

        sf.write(str(dest_path), combined, sample_rate, subtype="PCM_16")
        duration = _audio_duration_seconds(dest_path)
        if duration <= 0:
            raise TTSError(
                "synthesized audio duration is 0",
                scene_id=scene_id,
                scene_sequence=scene_sequence,
            )

        _logger.info(
            "TTS scene_id=%s seq=%s voice=%s duration=%.2fs path=%s",
            scene_id,
            scene_sequence,
            voice_name,
            duration,
            dest_path,
        )
        return {
            "path": str(dest_path),
            "duration_seconds": duration,
            "sample_rate": sample_rate,
            "voice": voice_name,
            "scene_id": scene_id,
            "sequence": scene_sequence,
            "mime_type": "audio/wav",
            "file_size": dest_path.stat().st_size,
        }
    except TTSError:
        raise
    except Exception as exc:
        raise TTSError(
            str(exc),
            scene_id=scene_id,
            scene_sequence=scene_sequence,
        ) from exc


def synthesize_video_scenes(
    video_payload: dict,
    audio_dir: Path | str,
    *,
    voice: str | None = None,
) -> list[dict[str, Any]]:
    """Create one WAV per scene from narration.

    Voice priority per scene:
      scene.voice → argument voice → video.tts_voice → env TTS_VOICE → maichi
    """
    out_dir = Path(audio_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    default_voice = (
        voice
        or (video_payload.get("tts_voice") or "").strip()
        or os.getenv("TTS_VOICE", "maichi")
    )
    results: list[dict[str, Any]] = []
    for scene in video_payload.get("scenes") or []:
        scene_id = scene.get("id")
        sequence = scene.get("sequence")
        scene_voice = (scene.get("voice") or scene.get("tts_voice") or "").strip()
        dest = out_dir / f"scene_{sequence or scene_id or 'x'}.wav"
        results.append(
            synthesize_to_wav(
                scene.get("narration") or "",
                dest,
                voice=scene_voice or default_voice,
                scene_id=scene_id,
                scene_sequence=sequence,
            )
        )
    return results
