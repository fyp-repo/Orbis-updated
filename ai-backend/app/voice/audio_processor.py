"""
OrbisERP Voice Pipeline — Audio Processing & VAD (Silero VAD)
============================================================
Handles audio format conversions, resampling to 16kHz 16-bit mono,
audio quality metrics, and neural Silero VAD (ONNX) speech segmentation.
"""

import io
import math
import struct
import numpy as np
import soundfile as sf
import torch
from typing import Dict, Any, Tuple


class AudioProcessor:
    """Processes incoming audio streams and files for VAD, STT, and Speaker Verification."""

    TARGET_SAMPLE_RATE = 16000
    _silero_model = None
    _silero_utils = None
    _vad_engine_name: str = "Silero VAD (neural ONNX)"

    def __init__(self, vad_mode: int = 2):
        self.vad_mode = vad_mode
        self._ensure_silero_loaded()

    @property
    def vad_engine(self) -> str:
        return self._vad_engine_name

    def _ensure_silero_loaded(self):
        """Loads Silero VAD ONNX model."""
        if AudioProcessor._silero_model is None:
            try:
                model, utils = torch.hub.load(
                    repo_or_dir="snakers4/silero-vad",
                    model="silero_vad",
                    onnx=True,
                    trust_repo=True,
                )
                AudioProcessor._silero_model = model
                AudioProcessor._silero_utils = utils
            except Exception as e:
                # If hub loading fails, fallback to WebRTC VAD
                import webrtcvad
                self._webrtc = webrtcvad.Vad(self.vad_mode)
                AudioProcessor._vad_engine_name = f"WebRTC VAD (mode={self.vad_mode} fallback: {e})"

    @classmethod
    def load_audio(cls, audio_bytes: bytes) -> Tuple[np.ndarray, int]:
        """
        Decodes arbitrary incoming audio (WAV, WebM, OGG, FLAC) into a float32 numpy array [-1.0, 1.0]
        and resamples to 16kHz mono.
        """
        if not audio_bytes:
            raise ValueError("Audio buffer is empty")

        try:
            # First attempt soundfile (fast for WAV/FLAC/OGG)
            data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        except Exception:
            # Fallback to PyAV for WebM / Opus containers common in browser recordings
            try:
                import av
                container = av.open(io.BytesIO(audio_bytes))
                resampler = av.AudioResampler(
                    format="fltp",
                    layout="mono",
                    rate=cls.TARGET_SAMPLE_RATE,
                )
                frames = []
                for frame in container.decode(audio=0):
                    resampled_frames = resampler.resample(frame)
                    for rf in resampled_frames:
                        frames.append(rf.to_ndarray())
                if not frames:
                    raise ValueError("No audio frames decoded")
                data = np.concatenate(frames, axis=1).squeeze()
                sr = cls.TARGET_SAMPLE_RATE
            except Exception as e:
                raise ValueError(f"Failed to decode audio data: {e}")

        # Convert multi-channel (stereo) to mono
        if len(data.shape) > 1 and data.shape[1] > 1:
            data = np.mean(data, axis=1)

        # Resample if not 16kHz
        if sr != cls.TARGET_SAMPLE_RATE:
            import scipy.signal
            target_length = int(len(data) * cls.TARGET_SAMPLE_RATE / sr)
            data = scipy.signal.resample(data, target_length).astype(np.float32)
            sr = cls.TARGET_SAMPLE_RATE

        # Normalize amplitude safely
        max_val = np.max(np.abs(data))
        if max_val > 0.001:
            data = data / max_val * 0.95

        return data.astype(np.float32), sr

    @classmethod
    def to_pcm16_bytes(cls, audio_float32: np.ndarray) -> bytes:
        """Converts float32 audio [-1.0, 1.0] to 16-bit signed integer PCM bytes."""
        clipped = np.clip(audio_float32, -1.0, 1.0)
        pcm16 = (clipped * 32767.0).astype(np.int16)
        return pcm16.tobytes()

    @classmethod
    def to_wav_bytes(cls, audio_float32: np.ndarray, sample_rate: int = 16000) -> bytes:
        """Encodes float32 array into standard WAV format bytes."""
        buffer = io.BytesIO()
        sf.write(buffer, audio_float32, sample_rate, format="WAV", subtype="PCM_16")
        return buffer.getvalue()

    def process_vad(self, audio_float32: np.ndarray) -> Dict[str, Any]:
        """
        Runs neural Silero VAD on audio, extracting speech ratio, speech segments,
        and trimmed speech audio.
        """
        if len(audio_float32) == 0:
            return {
                "has_speech": False,
                "speech_ratio": 0.0,
                "trimmed_audio": audio_float32,
                "duration_seconds": 0.0,
                "trimmed_duration_seconds": 0.0,
            }

        duration = float(len(audio_float32) / self.TARGET_SAMPLE_RATE)
        rms = float(np.sqrt(np.mean(np.square(audio_float32))))

        # Energy pre-check
        if rms < 0.008:
            return {
                "has_speech": False,
                "speech_ratio": 0.0,
                "trimmed_audio": audio_float32,
                "duration_seconds": duration,
                "trimmed_duration_seconds": 0.0,
            }

        # Run Silero VAD if loaded
        if AudioProcessor._silero_model is not None and AudioProcessor._silero_utils is not None:
            try:
                (get_speech_timestamps, _, _, _, collect_chunks) = AudioProcessor._silero_utils
                tensor = torch.from_numpy(audio_float32)
                timestamps = get_speech_timestamps(
                    tensor,
                    AudioProcessor._silero_model,
                    sampling_rate=self.TARGET_SAMPLE_RATE,
                    threshold=0.4,
                    min_speech_duration_ms=250,
                    min_silence_duration_ms=100,
                )

                if timestamps:
                    total_speech_samples = sum(ts["end"] - ts["start"] for ts in timestamps)
                    speech_ratio = float(total_speech_samples / len(audio_float32))
                    start_sample = max(0, timestamps[0]["start"] - int(self.TARGET_SAMPLE_RATE * 0.15))
                    end_sample = min(len(audio_float32), timestamps[-1]["end"] + int(self.TARGET_SAMPLE_RATE * 0.15))
                    trimmed = audio_float32[start_sample:end_sample]
                    has_speech = speech_ratio > 0.05
                else:
                    speech_ratio = 0.0
                    has_speech = False
                    trimmed = audio_float32

                return {
                    "has_speech": has_speech,
                    "speech_ratio": speech_ratio,
                    "trimmed_audio": trimmed,
                    "duration_seconds": duration,
                    "trimmed_duration_seconds": float(len(trimmed) / self.TARGET_SAMPLE_RATE),
                    "vad_engine": "Silero VAD",
                }
            except Exception:
                pass

        # Fallback to WebRTC VAD
        import webrtcvad
        vad = getattr(self, "_webrtc", None) or webrtcvad.Vad(self.vad_mode)
        pcm16_bytes = self.to_pcm16_bytes(audio_float32)
        frame_size = int(self.TARGET_SAMPLE_RATE * 0.030) * 2
        num_frames = len(pcm16_bytes) // frame_size
        if num_frames == 0:
            return {
                "has_speech": False,
                "speech_ratio": 0.0,
                "trimmed_audio": audio_float32,
                "duration_seconds": duration,
                "trimmed_duration_seconds": 0.0,
            }

        speech_flags = []
        speech_indices = []
        for i in range(num_frames):
            frame = pcm16_bytes[i * frame_size:(i + 1) * frame_size]
            is_speech = vad.is_speech(frame, self.TARGET_SAMPLE_RATE)
            speech_flags.append(is_speech)
            if is_speech:
                speech_indices.extend(range(i * 480, (i + 1) * 480))

        speech_ratio = sum(speech_flags) / len(speech_flags) if speech_flags else 0.0
        has_speech = speech_ratio > 0.08
        if has_speech and speech_indices:
            start_s = max(0, min(speech_indices) - int(self.TARGET_SAMPLE_RATE * 0.15))
            end_s = min(len(audio_float32), max(speech_indices) + int(self.TARGET_SAMPLE_RATE * 0.15))
            trimmed = audio_float32[start_s:end_s]
        else:
            trimmed = audio_float32

        return {
            "has_speech": has_speech,
            "speech_ratio": float(speech_ratio),
            "trimmed_audio": trimmed,
            "duration_seconds": duration,
            "trimmed_duration_seconds": float(len(trimmed) / self.TARGET_SAMPLE_RATE),
            "vad_engine": "WebRTC VAD (fallback)",
        }

    @staticmethod
    def calculate_quality(audio_float32: np.ndarray) -> Dict[str, Any]:
        """
        Assesses audio sample quality (RMS energy, clipping, duration)
        to prevent enrolling noisy or silent audio.
        """
        duration = len(audio_float32) / 16000.0
        if len(audio_float32) == 0:
            return {"is_valid": False, "reason": "Empty audio buffer", "rms": 0.0}

        rms = float(np.sqrt(np.mean(np.square(audio_float32))))
        clipped_ratio = float(np.sum(np.abs(audio_float32) >= 0.99) / len(audio_float32))

        if duration < 0.6:
            return {"is_valid": False, "reason": "Audio too short (minimum 0.6s required)", "rms": rms, "duration": duration}
        if rms < 0.012:
            return {"is_valid": False, "reason": "Audio volume too quiet / low signal", "rms": rms, "duration": duration}
        if clipped_ratio > 0.20:
            return {"is_valid": False, "reason": "Audio distorted / heavy clipping", "rms": rms, "duration": duration}

        return {
            "is_valid": True,
            "rms": rms,
            "duration": duration,
            "clipped_ratio": clipped_ratio,
        }
