import math
import wave
import struct
from pathlib import Path


def generate_sine_wav(path: Path, duration_sec: float, freq_hz: float = 440.0, volume: float = 0.2) -> None:
    """
    단일 채널 sine wave WAV 생성.
    """
    sample_rate = 44100
    n_frames = int(duration_sec * sample_rate)
    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)

        for i in range(n_frames):
            t = i / sample_rate
            sample = volume * math.sin(2.0 * math.pi * freq_hz * t)
            sample_int = int(max(-1.0, min(1.0, sample)) * 32767)
            wf.writeframes(struct.pack("<h", sample_int))


def get_wav_duration(path: Path) -> float:
    """
    nframes / framerate 기반 duration 계산.
    """
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        if rate == 0:
            return 0.0
        return frames / float(rate)

