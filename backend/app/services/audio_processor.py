"""
Audio Processor Service

Provides FFmpeg-based audio processing functionality:
- Waveform data generation
- Audio duration
- Split audio at specific points
- Trim audio (keep or delete selection)
- Merge multiple audio files
"""

import os
import json
import tempfile
import subprocess
from typing import List, Optional, Tuple
from pathlib import Path


SUPPORTED_AUDIO_EXTENSIONS = {
    '.mp3', '.wav', '.flac', '.m4a', '.m4b', '.aac', '.ogg', '.opus',
    '.wma', '.ape', '.wv', '.mka', '.webm', '.ac3',
}


def is_mp3(filename: str) -> bool:
    """Check if a filename has an MP3 extension."""
    return Path(filename).suffix.lower() == '.mp3'


def convert_to_mp3(
    input_path: str,
    output_path: Optional[str] = None,
    quality: int = 2,
) -> str:
    """
    Convert any audio file to MP3 using FFmpeg.

    Args:
        input_path: Path to the source audio file
        output_path: Optional output path (creates temp file if not provided)
        quality: VBR quality (0=best, 9=worst, default 2 ≈ 190kbps)

    Returns:
        Path to the MP3 file
    """
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".mp3", prefix="yoto_convert_")
        os.close(fd)

    cmd = [
        get_ffmpeg_path(),
        "-i", input_path,
        "-acodec", "libmp3lame",
        "-q:a", str(quality),
        "-y",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg MP3 conversion failed: {result.stderr.decode()}")

    return output_path


def get_ffmpeg_path() -> str:
    """Get the path to the ffmpeg executable."""
    return "ffmpeg"


def get_ffprobe_path() -> str:
    """Get the path to the ffprobe executable."""
    return "ffprobe"


def get_audio_duration(audio_path: str) -> int:
    """
    Get the duration of an audio file in milliseconds.

    Args:
        audio_path: Path to the audio file

    Returns:
        Duration in milliseconds
    """
    cmd = [
        get_ffprobe_path(),
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "json",
        audio_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    data = json.loads(result.stdout)
    duration_seconds = float(data["format"]["duration"])
    return int(duration_seconds * 1000)


def get_waveform_data(audio_path: str, samples: int = 800) -> List[float]:
    """
    Generate waveform data from an audio file.

    Uses FFmpeg to extract audio samples and normalize them for visualization.

    Args:
        audio_path: Path to the audio file
        samples: Number of samples to generate (default 800 for good resolution)

    Returns:
        List of normalized amplitude values (0.0 to 1.0)
    """
    # Get duration first
    duration_ms = get_audio_duration(audio_path)
    duration_s = duration_ms / 1000.0

    # Calculate samples per second
    samples_per_second = samples / duration_s

    # Create a temporary file for the raw audio data
    with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Extract mono audio samples at reduced sample rate
        target_sample_rate = int(samples_per_second * 10)  # 10 samples per waveform point
        target_sample_rate = max(100, min(target_sample_rate, 8000))

        cmd = [
            get_ffmpeg_path(),
            "-i", audio_path,
            "-ac", "1",  # Mono
            "-ar", str(target_sample_rate),
            "-f", "s16le",  # Raw 16-bit signed little-endian
            "-acodec", "pcm_s16le",
            "-y",
            tmp_path
        ]

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")

        # Read the raw audio data
        with open(tmp_path, "rb") as f:
            raw_data = f.read()

        # Convert to samples
        import struct
        num_samples = len(raw_data) // 2
        audio_samples = list(struct.unpack(f"<{num_samples}h", raw_data))

        if not audio_samples:
            return [0.0] * samples

        # Find the maximum amplitude for normalization
        max_amplitude = max(abs(min(audio_samples)), abs(max(audio_samples)), 1)

        # Downsample to target number of samples
        samples_per_point = max(1, len(audio_samples) // samples)
        waveform = []

        for i in range(samples):
            start = i * samples_per_point
            end = min(start + samples_per_point, len(audio_samples))

            if start >= len(audio_samples):
                waveform.append(0.0)
                continue

            # Get the peak amplitude in this segment
            segment = audio_samples[start:end]
            if segment:
                peak = max(abs(min(segment)), abs(max(segment)))
                normalized = peak / max_amplitude
                waveform.append(round(normalized, 4))
            else:
                waveform.append(0.0)

        return waveform

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def split_audio(
    audio_path: str,
    split_points: List[int],
    output_dir: Optional[str] = None
) -> List[str]:
    """
    Split an audio file at specific timestamps.

    Args:
        audio_path: Path to the audio file
        split_points: List of timestamps in milliseconds where to split
        output_dir: Optional output directory (uses temp dir if not provided)

    Returns:
        List of paths to the split audio files
    """
    if not split_points:
        raise ValueError("At least one split point is required")

    # Get duration
    duration_ms = get_audio_duration(audio_path)

    # Sort split points and add start/end
    points = sorted(set(split_points))
    points = [p for p in points if 0 < p < duration_ms]

    if not points:
        raise ValueError("No valid split points within audio duration")

    segments = []
    segments.append((0, points[0]))
    for i in range(len(points) - 1):
        segments.append((points[i], points[i + 1]))
    segments.append((points[-1], duration_ms))

    # Create output directory
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="yoto_split_")

    output_files = []
    file_ext = Path(audio_path).suffix

    for i, (start_ms, end_ms) in enumerate(segments):
        output_path = os.path.join(output_dir, f"segment_{i:03d}{file_ext}")

        start_s = start_ms / 1000.0
        duration_s = (end_ms - start_ms) / 1000.0

        cmd = [
            get_ffmpeg_path(),
            "-i", audio_path,
            "-ss", str(start_s),
            "-t", str(duration_s),
            "-c", "copy",  # Copy codec for speed
            "-y",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            # Try with re-encoding if copy fails
            cmd = [
                get_ffmpeg_path(),
                "-i", audio_path,
                "-ss", str(start_s),
                "-t", str(duration_s),
                "-acodec", "libmp3lame",
                "-q:a", "2",
                "-y",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")

        output_files.append(output_path)

    return output_files


def trim_audio(
    audio_path: str,
    start_ms: int,
    end_ms: int,
    mode: str = "keep",
    output_path: Optional[str] = None
) -> str:
    """
    Trim an audio file.

    Args:
        audio_path: Path to the audio file
        start_ms: Start timestamp in milliseconds
        end_ms: End timestamp in milliseconds
        mode: "keep" to keep the selection, "delete" to remove it
        output_path: Optional output path (creates temp file if not provided)

    Returns:
        Path to the trimmed audio file
    """
    duration_ms = get_audio_duration(audio_path)

    if start_ms < 0:
        start_ms = 0
    if end_ms > duration_ms:
        end_ms = duration_ms
    if start_ms >= end_ms:
        raise ValueError("Invalid selection range")

    file_ext = Path(audio_path).suffix

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=file_ext, prefix="yoto_trim_")
        os.close(fd)

    if mode == "keep":
        # Keep only the selected portion
        start_s = start_ms / 1000.0
        duration_s = (end_ms - start_ms) / 1000.0

        cmd = [
            get_ffmpeg_path(),
            "-i", audio_path,
            "-ss", str(start_s),
            "-t", str(duration_s),
            "-c", "copy",
            "-y",
            output_path
        ]
    else:
        # Delete the selection (keep before and after)
        # This requires creating two segments and concatenating

        with tempfile.TemporaryDirectory(prefix="yoto_trim_") as tmp_dir:
            segments = []

            # Before selection
            if start_ms > 0:
                before_path = os.path.join(tmp_dir, f"before{file_ext}")
                cmd = [
                    get_ffmpeg_path(),
                    "-i", audio_path,
                    "-t", str(start_ms / 1000.0),
                    "-c", "copy",
                    "-y",
                    before_path
                ]
                result = subprocess.run(cmd, capture_output=True)
                if result.returncode == 0:
                    segments.append(before_path)

            # After selection
            if end_ms < duration_ms:
                after_path = os.path.join(tmp_dir, f"after{file_ext}")
                cmd = [
                    get_ffmpeg_path(),
                    "-i", audio_path,
                    "-ss", str(end_ms / 1000.0),
                    "-c", "copy",
                    "-y",
                    after_path
                ]
                result = subprocess.run(cmd, capture_output=True)
                if result.returncode == 0:
                    segments.append(after_path)

            if not segments:
                raise ValueError("Nothing left after trimming")

            if len(segments) == 1:
                # Just copy the single segment
                import shutil
                shutil.copy(segments[0], output_path)
            else:
                # Concatenate segments
                return merge_audio(segments, output_path)

            return output_path

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        # Try with re-encoding
        cmd[-4] = "-acodec"
        cmd[-3] = "libmp3lame"
        cmd.insert(-2, "-q:a")
        cmd.insert(-2, "2")
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")

    return output_path


def merge_audio(
    audio_paths: List[str],
    output_path: Optional[str] = None
) -> str:
    """
    Merge multiple audio files into one.

    Args:
        audio_paths: List of paths to audio files
        output_path: Optional output path (creates temp file if not provided)

    Returns:
        Path to the merged audio file
    """
    if not audio_paths:
        raise ValueError("At least one audio file is required")

    if len(audio_paths) == 1:
        if output_path:
            import shutil
            shutil.copy(audio_paths[0], output_path)
            return output_path
        return audio_paths[0]

    file_ext = Path(audio_paths[0]).suffix

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=file_ext, prefix="yoto_merge_")
        os.close(fd)

    # Create a concat file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        concat_file = f.name
        for path in audio_paths:
            # Escape single quotes in paths
            escaped_path = path.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")

    try:
        cmd = [
            get_ffmpeg_path(),
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            "-y",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            # Try with re-encoding if copy fails
            cmd = [
                get_ffmpeg_path(),
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-acodec", "libmp3lame",
                "-q:a", "2",
                "-y",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")

        return output_path

    finally:
        if os.path.exists(concat_file):
            os.remove(concat_file)


def get_audio_info(audio_path: str) -> dict:
    """
    Get detailed information about an audio file.

    Args:
        audio_path: Path to the audio file

    Returns:
        Dict with duration, format, bitrate, sample_rate, channels
    """
    cmd = [
        get_ffprobe_path(),
        "-v", "quiet",
        "-show_format",
        "-show_streams",
        "-select_streams", "a:0",
        "-of", "json",
        audio_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    data = json.loads(result.stdout)

    format_info = data.get("format", {})
    stream_info = data.get("streams", [{}])[0]

    return {
        "duration_ms": int(float(format_info.get("duration", 0)) * 1000),
        "format": format_info.get("format_name"),
        "bitrate": int(format_info.get("bit_rate", 0)),
        "sample_rate": int(stream_info.get("sample_rate", 0)),
        "channels": int(stream_info.get("channels", 0)),
    }
