"""Render vertical MP4 (9:16) from scene images + audio. No subtitles."""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920
DEFAULT_FPS = 30
DEFAULT_TRANSITION_SECONDS = 0.4
DEFAULT_KEN_BURNS_ZOOM = 1.08


class RenderError(Exception):
    """Raised when FFmpeg render fails."""


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _ffmpeg_bin() -> str:
    return os.getenv("FFMPEG_BIN", "ffmpeg")


def _ffprobe_bin() -> str:
    return os.getenv("FFPROBE_BIN", "ffprobe")


def _run(cmd: list[str], *, label: str) -> None:
    _logger.debug("Running %s: %s", label, " ".join(cmd))
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RenderError(
            f"{label} failed: ffmpeg/ffprobe not found. Install FFmpeg and ensure it is on PATH."
        ) from exc
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").strip()
        raise RenderError(f"{label} failed (code {completed.returncode}): {err[-2000:]}")


def probe_media(path: Path) -> dict[str, Any]:
    cmd = [
        _ffprobe_bin(),
        "-v",
        "error",
        "-show_entries",
        "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RenderError("ffprobe not found on PATH") from exc
    if completed.returncode != 0:
        raise RenderError(f"ffprobe failed for {path}: {completed.stderr[-1000:]}")
    try:
        return json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RenderError(f"ffprobe returned invalid JSON for {path}") from exc


def validate_output_mp4(
    path: Path,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    min_duration: float = 0.1,
) -> dict[str, Any]:
    if not path.exists():
        raise RenderError(f"Output file missing: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise RenderError(f"Output file is empty: {path}")

    probe = probe_media(path)
    fmt = probe.get("format") or {}
    duration = float(fmt.get("duration") or 0)
    if duration < min_duration:
        raise RenderError(f"Output duration too short: {duration}s")

    video_stream = next(
        (s for s in (probe.get("streams") or []) if s.get("codec_type") == "video"),
        None,
    )
    audio_stream = next(
        (s for s in (probe.get("streams") or []) if s.get("codec_type") == "audio"),
        None,
    )
    if not video_stream:
        raise RenderError("Output has no video stream")
    if not audio_stream:
        raise RenderError("Output has no audio stream")

    vw = int(video_stream.get("width") or 0)
    vh = int(video_stream.get("height") or 0)
    if vw != width or vh != height:
        raise RenderError(f"Unexpected resolution {vw}x{vh}, expected {width}x{height}")

    # Ensure no subtitle stream
    if any(s.get("codec_type") == "subtitle" for s in (probe.get("streams") or [])):
        raise RenderError("Output unexpectedly contains a subtitle stream")

    return {
        "path": str(path),
        "file_size": size,
        "duration_seconds": duration,
        "width": vw,
        "height": vh,
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
        "mime_type": "video/mp4",
    }


def _scene_still_filter(
    input_index: int,
    out_label: str,
    *,
    image_fit: str,
    width: int,
    height: int,
    fps: int,
    duration: float,
    ken_burns: bool,
    zoom_end: float,
) -> str:
    """Build filter graph fragment: still image → timed 9:16 clip with optional slow zoom."""
    fit = (image_fit or "blur_background").strip().lower()
    idx = input_index
    tag = out_label

    if fit == "crop":
        composed = (
            f"[{idx}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1[c{tag}]"
        )
    else:
        composed = (
            f"[{idx}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},boxblur=20:5[bg{tag}];"
            f"[{idx}:v]scale={width}:{height}:force_original_aspect_ratio=decrease[fg{tag}];"
            f"[bg{tag}][fg{tag}]overlay=(W-w)/2:(H-h)/2,setsar=1[c{tag}]"
        )

    if ken_burns and zoom_end > 1.001:
        # Slow zoom + slight pan so stills feel continuous (not a frozen frame then hard cut).
        sw = int(width * zoom_end)
        sh = int(height * zoom_end)
        sw += sw % 2
        sh += sh % 2
        motion = (
            f"[c{tag}]scale={sw}:{sh},"
            f"crop={width}:{height}:"
            f"x='(in_w-out_w)*t/{duration:.3f}':"
            f"y='(in_h-out_h)*t/{duration:.3f}*0.5',"
            f"fps={fps},format=yuv420p,trim=duration={duration:.3f},"
            f"setpts=PTS-STARTPTS,settb=AVTB[{tag}]"
        )
    else:
        motion = (
            f"[c{tag}]fps={fps},format=yuv420p,trim=duration={duration:.3f},"
            f"setpts=PTS-STARTPTS,settb=AVTB[{tag}]"
        )
    return f"{composed};{motion}"


def _scene_audio_filter(input_index: int, out_label: str, *, duration: float) -> str:
    """Normalize audio and trim/pad to exact scene duration (avoids A/V gaps at cuts)."""
    return (
        f"[{input_index}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
        f"atrim=0:{duration:.3f},apad=whole_dur={duration:.3f},asetpts=PTS-STARTPTS[{out_label}]"
    )


def render_scene_clip(
    image_path: Path,
    audio_path: Path,
    dest_path: Path,
    *,
    duration_seconds: float,
    image_fit: str = "blur_background",
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    fps: int = DEFAULT_FPS,
    ken_burns: bool | None = None,
    zoom_end: float | None = None,
) -> Path:
    if duration_seconds <= 0:
        raise RenderError(f"Invalid scene duration: {duration_seconds}")
    if not Path(image_path).exists():
        raise RenderError(f"Image missing: {image_path}")
    if not Path(audio_path).exists():
        raise RenderError(f"Audio missing: {audio_path}")

    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    use_kb = _env_bool("SCENE_KEN_BURNS", True) if ken_burns is None else ken_burns
    zoom = zoom_end if zoom_end is not None else _env_float("SCENE_KEN_BURNS_ZOOM", DEFAULT_KEN_BURNS_ZOOM)
    vfilt = _scene_still_filter(
        0,
        "v",
        image_fit=image_fit,
        width=width,
        height=height,
        fps=fps,
        duration=duration_seconds,
        ken_burns=use_kb,
        zoom_end=zoom,
    )
    afilt = _scene_audio_filter(1, "a", duration=duration_seconds)
    cmd = [
        _ffmpeg_bin(),
        "-y",
        "-loop",
        "1",
        "-t",
        f"{duration_seconds:.3f}",
        "-i",
        str(image_path),
        "-i",
        str(audio_path),
        "-filter_complex",
        f"{vfilt};{afilt}",
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-t",
        f"{duration_seconds:.3f}",
        "-movflags",
        "+faststart",
        str(dest_path),
    ]
    _run(cmd, label=f"render scene {dest_path.name}")
    return dest_path


def _concat_clips_reencode(clip_paths: list[Path], dest_path: Path) -> Path:
    """Concat with re-encode (safer timestamps than stream copy)."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = dest_path.with_suffix(".txt")
    lines = []
    for clip in clip_paths:
        safe = str(clip).replace("'", r"'\''")
        lines.append(f"file '{safe}'")
    list_file.write_text("\n".join(lines), encoding="utf-8")
    try:
        cmd = [
            _ffmpeg_bin(),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(dest_path),
        ]
        _run(cmd, label="concat clips")
    finally:
        list_file.unlink(missing_ok=True)
    return dest_path


def _render_with_crossfade(
    scenes: list[dict[str, Any]],
    dest_path: Path,
    *,
    image_fit: str,
    width: int,
    height: int,
    fps: int,
    transition: float,
    ken_burns: bool,
    zoom_end: float,
) -> Path:
    """One-pass render: soft xfade on video + acrossfade on narration."""
    durations = [float(s["duration_seconds"]) for s in scenes]
    # Keep transition shorter than every scene (xfade requires offset > 0).
    max_allowed = min(durations) * 0.45
    t = max(0.05, min(transition, max_allowed)) if transition > 0 else 0.0
    if t <= 0 or len(scenes) < 2:
        raise RenderError("crossfade requires >=2 scenes and transition > 0")

    cmd: list[str] = [_ffmpeg_bin(), "-y"]
    filter_parts: list[str] = []
    for i, scene in enumerate(scenes):
        dur = durations[i]
        cmd.extend(
            [
                "-loop",
                "1",
                "-t",
                f"{dur:.3f}",
                "-i",
                str(scene["image_path"]),
                "-i",
                str(scene["audio_path"]),
            ]
        )
        img_idx = i * 2
        aud_idx = i * 2 + 1
        filter_parts.append(
            _scene_still_filter(
                img_idx,
                f"v{i}",
                image_fit=image_fit,
                width=width,
                height=height,
                fps=fps,
                duration=dur,
                ken_burns=ken_burns,
                zoom_end=zoom_end,
            )
        )
        filter_parts.append(_scene_audio_filter(aud_idx, f"a{i}", duration=dur))

    # Chain xfade / acrossfade
    v_prev = "v0"
    a_prev = "a0"
    offset = durations[0] - t
    for i in range(1, len(scenes)):
        v_out = f"vx{i}"
        a_out = f"ax{i}"
        filter_parts.append(
            f"[{v_prev}][v{i}]xfade=transition=fade:duration={t:.3f}:offset={offset:.3f}[{v_out}]"
        )
        filter_parts.append(
            f"[{a_prev}][a{i}]acrossfade=d={t:.3f}:c1=tri:c2=tri[{a_out}]"
        )
        v_prev, a_prev = v_out, a_out
        if i + 1 < len(scenes):
            offset += durations[i] - t

    # Gentle bookend fades so open/close aren't abrupt.
    edge = min(0.25, t)
    total = sum(durations) - t * (len(scenes) - 1)
    fade_out_start = max(0.0, total - edge)
    filter_parts.append(
        f"[{v_prev}]fade=t=in:st=0:d={edge:.3f},"
        f"fade=t=out:st={fade_out_start:.3f}:d={edge:.3f}[vout]"
    )
    filter_parts.append(
        f"[{a_prev}]afade=t=in:st=0:d={edge:.3f},"
        f"afade=t=out:st={fade_out_start:.3f}:d={edge:.3f}[aout]"
    )

    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    cmd.extend(
        [
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(dest_path),
        ]
    )
    _logger.info(
        "Crossfade render scenes=%s transition=%.2fs ken_burns=%s",
        len(scenes),
        t,
        ken_burns,
    )
    _run(cmd, label="crossfade render")
    return dest_path


def _mix_background_music(
    video_path: Path,
    music_path: Path,
    dest_path: Path,
    *,
    music_volume: float = 0.12,
) -> Path:
    dest_path = Path(dest_path)
    cmd = [
        _ffmpeg_bin(),
        "-y",
        "-i",
        str(video_path),
        "-stream_loop",
        "-1",
        "-i",
        str(music_path),
        "-filter_complex",
        f"[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
        "-map",
        "0:v",
        "-map",
        "[a]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(dest_path),
    ]
    _run(cmd, label="mix background music")
    return dest_path


def render_vertical_video(
    scenes: list[dict[str, Any]],
    output_path: Path | str,
    *,
    image_fit: str = "blur_background",
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    fps: int = DEFAULT_FPS,
    music_path: str | Path | None = None,
    music_volume: float = 0.12,
    work_dir: Path | str | None = None,
    transition_seconds: float | None = None,
    ken_burns: bool | None = None,
) -> dict[str, Any]:
    """Render final MP4 from scene dicts with image_path/audio_path/duration_seconds.

    Soft crossfade between scenes by default (SCENE_TRANSITION_SECONDS, default 0.4).
    Still images get a light Ken Burns zoom (SCENE_KEN_BURNS=1).
    """
    if not scenes:
        raise RenderError("No scenes to render")

    output_path = Path(output_path)
    base_dir = Path(work_dir) if work_dir else output_path.parent
    base_dir.mkdir(parents=True, exist_ok=True)

    prepared: list[dict[str, Any]] = []
    for scene in scenes:
        image_path = Path(scene["image_path"])
        audio_path = Path(scene["audio_path"])
        duration = float(scene.get("duration_seconds") or 0)
        if duration <= 0:
            raise RenderError(f"Invalid scene duration: {duration}")
        if not image_path.exists():
            raise RenderError(f"Image missing: {image_path}")
        if not audio_path.exists():
            raise RenderError(f"Audio missing: {audio_path}")
        prepared.append(
            {
                "image_path": image_path,
                "audio_path": audio_path,
                "duration_seconds": duration,
            }
        )

    if transition_seconds is None:
        transition = _env_float("SCENE_TRANSITION_SECONDS", DEFAULT_TRANSITION_SECONDS)
    else:
        transition = float(transition_seconds)
    if ken_burns is None:
        ken_burns = _env_bool("SCENE_KEN_BURNS", True)
    zoom_end = _env_float("SCENE_KEN_BURNS_ZOOM", DEFAULT_KEN_BURNS_ZOOM)

    concat_path = base_dir / "concat_no_music.mp4"
    use_crossfade = len(prepared) >= 2 and transition > 0

    if use_crossfade:
        try:
            _render_with_crossfade(
                prepared,
                concat_path,
                image_fit=image_fit,
                width=width,
                height=height,
                fps=fps,
                transition=transition,
                ken_burns=ken_burns,
                zoom_end=zoom_end,
            )
        except RenderError:
            _logger.warning("Crossfade failed; falling back to hard concat", exc_info=True)
            use_crossfade = False

    if not use_crossfade:
        clips_dir = base_dir / "clips"
        if clips_dir.exists():
            shutil.rmtree(clips_dir, ignore_errors=True)
        clips_dir.mkdir(parents=True, exist_ok=True)
        clip_paths: list[Path] = []
        for index, scene in enumerate(prepared, start=1):
            clip = clips_dir / f"scene_{index:03d}.mp4"
            render_scene_clip(
                scene["image_path"],
                scene["audio_path"],
                clip,
                duration_seconds=scene["duration_seconds"],
                image_fit=image_fit,
                width=width,
                height=height,
                fps=fps,
                ken_burns=ken_burns,
                zoom_end=zoom_end,
            )
            clip_paths.append(clip)
        if len(clip_paths) == 1:
            shutil.copy2(clip_paths[0], concat_path)
        else:
            _concat_clips_reencode(clip_paths, concat_path)

    final_tmp = output_path
    if music_path and Path(music_path).exists():
        mixed = base_dir / "final_mixed.mp4"
        _mix_background_music(
            concat_path,
            Path(music_path),
            mixed,
            music_volume=music_volume,
        )
        shutil.copy2(mixed, final_tmp)
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(concat_path, final_tmp)

    meta = validate_output_mp4(Path(final_tmp), width=width, height=height)
    _logger.info(
        "Rendered %s (%.2fs, %sx%s, %s bytes)",
        meta["path"],
        meta["duration_seconds"],
        meta["width"],
        meta["height"],
        meta["file_size"],
    )
    return meta
