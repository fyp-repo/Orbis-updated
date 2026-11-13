"""
OrbisERP Voice Pipeline — Text-to-Speech (TTS) Engine
=====================================================
Synthesizes spoken audio from text responses.
Primary: Edge-TTS (online neural speech synthesis).
Fallback: Local WAV audio tone generator (offline fallback).
Returns base64 audio and metadata.
"""

import asyncio
import base64
import io
import numpy as np
import soundfile as sf
import edge_tts


class TTSEngine:
    """Manages text-to-speech generation with online Edge-TTS and offline audio fallback."""

    DEFAULT_VOICE = "en-US-AriaNeural"

    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice

    async def synthesize(self, text: str) -> dict:
        """
        Synthesizes speech from text.
        Attempts Edge-TTS first; gracefully falls back to local synthesis if offline.
        """
        if not text or not text.strip():
            return {
                "audio_base64": "",
                "audio_format": "audio/wav",
                "text": "",
                "engine": "none",
                "is_online": False,
            }

        cleaned_text = text.strip()

        # 1. Attempt Edge-TTS (High Quality Neural Speech - Online)
        try:
            communicate = edge_tts.Communicate(cleaned_text, self.voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            if audio_data:
                b64 = base64.b64encode(audio_data).decode("utf-8")
                return {
                    "audio_base64": b64,
                    "audio_format": "audio/mp3",
                    "text": cleaned_text,
                    "engine": f"edge-tts ({self.voice})",
                    "is_online": True,
                }
        except Exception:
            # Fall back to offline audio generation
            pass

        # 2. Offline Fallback Generator (Generates valid WAV audio tone sequence)
        fallback_wav = self._generate_offline_chime()
        b64 = base64.b64encode(fallback_wav).decode("utf-8")
        return {
            "audio_base64": b64,
            "audio_format": "audio/wav",
            "text": cleaned_text,
            "engine": "local-wav-chime (offline fallback)",
            "is_online": False,
        }

    @staticmethod
    def _generate_offline_chime() -> bytes:
        """Generates a pleasant 2-tone melodic confirmation chime as offline fallback."""
        sr = 16000
        duration_per_tone = 0.18
        t1 = np.linspace(0, duration_per_tone, int(sr * duration_per_tone), endpoint=False)
        t2 = np.linspace(0, duration_per_tone, int(sr * duration_per_tone), endpoint=False)

        # 440 Hz (A4) followed by 880 Hz (A5)
        tone1 = 0.4 * np.sin(2 * np.pi * 523.25 * t1) * np.exp(-3 * t1)  # C5
        tone2 = 0.4 * np.sin(2 * np.pi * 659.25 * t2) * np.exp(-3 * t2)  # E5
        chime = np.concatenate([tone1, tone2]).astype(np.float32)

        buf = io.BytesIO()
        sf.write(buf, chime, sr, format="WAV", subtype="PCM_16")
        return buf.getvalue()

