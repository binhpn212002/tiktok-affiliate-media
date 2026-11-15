import os
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

import requests
from PIL import Image

from odoo import _
from odoo.exceptions import UserError


def allowed_image_url(url):
    if not isinstance(url, str):
        return False
    try:
        target = urlsplit(url)
        base = urlsplit(os.environ.get("R2_PUBLIC_BASE_URL", ""))
        return (
            target.scheme == base.scheme == "https"
            and target.netloc == base.netloc
            and bool(target.hostname)
            and target.path.startswith(base.path.rstrip("/") + "/")
            and not target.username
            and not target.fragment
        )
    except ValueError:
        return False


def _download_image(url, dest):
    if not allowed_image_url(url):
        raise ValueError("Image URL is outside the configured R2 bucket")
    with requests.get(url, stream=True, timeout=(5, 15), allow_redirects=False) as response:
        if response.status_code != 200:
            raise ValueError(f"R2 returned HTTP {response.status_code}")
        size = 0
        with dest.open("wb") as file:
            for chunk in response.iter_content(64 * 1024):
                size += len(chunk)
                if size > 10 * 1024 * 1024:
                    raise ValueError("Image exceeds 10 MB")
                file.write(chunk)
    with Image.open(dest) as image:
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError("Expected a JPEG, PNG or WebP image")
        image.verify()


def render_video(scenes, voice):
    from .ffmpeg_renderer import render_vertical_video
    from .tts_service import synthesize_to_wav

    with TemporaryDirectory(prefix="affiliate-video-") as directory:
        work_dir = Path(directory)
        clips = []
        for scene in scenes:
            sequence = scene["sequence"]
            image = work_dir / f"image-{sequence}"
            try:
                _download_image(scene["image_url"], image)
            except (OSError, ValueError, requests.RequestException, Image.DecompressionBombError) as error:
                raise UserError(_("Scene %(scene)s: could not read the R2 image.", scene=sequence)) from error
            try:
                audio = synthesize_to_wav(
                    scene["narration"], work_dir / f"audio-{sequence}.wav",
                    voice=voice, scene_sequence=sequence,
                )
            except Exception as error:
                raise UserError(_("Scene %(scene)s: ZeroTTS failed. Check the server log.", scene=sequence)) from error
            clips.append({
                "image_path": image,
                "audio_path": audio["path"],
                "duration_seconds": audio["duration_seconds"],
            })

        output = work_dir / "video.mp4"
        render_vertical_video(clips, output, work_dir=work_dir, transition_seconds=0, ken_burns=False)
        return output.read_bytes()
