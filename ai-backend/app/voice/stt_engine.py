"""
OrbisERP Voice Pipeline — Speech-to-Text & Wake Word Spotter
============================================================
Runs faster-whisper on local CPU with int8 quantization.
Includes wake-word identification for "Orbis".
"""

import re
import numpy as np
from faster_whisper import WhisperModel

# Common wake word trigger patterns for "Orbis"
WAKE_PATTERNS = [
    re.compile(r"\b(orbis|orbi|albis|orbiss|aurbis|orvis)\b", re.IGNORECASE),
    re.compile(r"\b(hey|hi|hello|ok|activate|wake)\s+(orbis|orbi|albis)\b", re.IGNORECASE),
]


class STTEngine:
    """Lazy-loaded faster-whisper instance optimized for CPU inference."""

    _instance = None
    _model = None

    def __init__(self, model_size: str = "base.en", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    def _get_model(self) -> WhisperModel:
        if STTEngine._model is None:
            # Lazy initialize model on CPU with int8 quantization to conserve memory
            STTEngine._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=4,
                num_workers=1,
            )
        return STTEngine._model

    def transcribe(self, audio_float32: np.ndarray) -> dict:
        """
        Transcribes 16kHz float32 audio to text using faster-whisper.
        """
        if len(audio_float32) == 0:
            return {"text": "", "language": "en", "confidence": 0.0, "segments": []}

        model = self._get_model()
        segments, info = model.transcribe(
            audio_float32,
            beam_size=1,  # Greedy search for fastest CPU response
            language="en",
            vad_filter=False,  # Already filtered by our VAD
            word_timestamps=False,
        )

        full_text = " ".join([seg.text.strip() for seg in segments]).strip()
        
        # Check wake word presence
        has_wake_word = self.has_wake_word(full_text)

        # Strip wake-word prefix from query so "Orbis check stock" becomes "check stock"
        clean_text = self.strip_wake_word(full_text)

        return {
            "text": full_text,
            "clean_query": clean_text,
            "has_wake_word": has_wake_word,
            "language": info.language,
            "duration": info.duration,
        }

    @staticmethod
    def has_wake_word(text: str) -> bool:
        """Determines if the transcript contains the wake word 'Orbis'."""
        if not text:
            return False
        return any(p.search(text) for p in WAKE_PATTERNS)

    @staticmethod
    def strip_wake_word(text: str) -> str:
        """Removes the wake word from the query for clean intent routing."""
        if not text:
            return ""
        # Remove patterns like "Hey Orbis", "Orbis", "Activate Orbis" from beginning
        cleaned = re.sub(r"^(hey|hi|hello|ok|activate)?\s*(orbis|orbi|albis)[,\s]*", "", text, flags=re.IGNORECASE)
        return cleaned.strip()

