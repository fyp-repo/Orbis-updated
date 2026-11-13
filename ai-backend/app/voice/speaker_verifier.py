"""
OrbisERP Voice Pipeline — Speaker Identification & Voice Biometrics
===================================================================
Uses genuine SpeechBrain ECAPA-TDNN (speechbrain/spkrec-ecapa-voxceleb)
to generate 192-dimensional speaker voiceprints and verify identity
using cosine similarity. Fails closed if ECAPA cannot load.
Persists profiles in local SQLite database (voice_profiles.db).
"""

import os
import sqlite3
import numpy as np
import torch
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from app.core.config import settings

AI_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = AI_BACKEND_DIR / "voice_profiles.db"
LOCAL_ECAPA_DIR = AI_BACKEND_DIR / "models" / "ecapa"


class SpeakerVerifier:
    """Manages voice biometrics, ECAPA-TDNN feature extraction, and speaker matching."""

    _instance = None
    _classifier = None
    _model_loaded: bool = False
    _model_load_error: Optional[str] = None
    _embedding_dimension: int = 192
    _device: str = "cpu"
    _model_name: str = "speechbrain/spkrec-ecapa-voxceleb"

    def __init__(self, db_path: Path = DB_PATH, threshold: Optional[float] = None):
        self.db_path = db_path
        self.threshold = threshold if threshold is not None else settings.orbis_voice_similarity_threshold
        self._init_db()
        self._ensure_ecapa_loaded()

    @property
    def biometric_engine(self) -> str:
        """Returns the biometric engine description."""
        if self._model_loaded:
            return "SpeechBrain ECAPA-TDNN (neural)"
        return "Uninitialized / Biometric Engine Offline"

    @property
    def engine_name(self) -> str:
        """Alias for biometric_engine."""
        return self.biometric_engine

    @property
    def model_loaded(self) -> bool:
        return self._model_loaded

    @property
    def model_load_error(self) -> Optional[str]:
        return self._model_load_error

    @property
    def embedding_dimension(self) -> int:
        return self._embedding_dimension

    @property
    def device(self) -> str:
        return self._device

    @property
    def model_name(self) -> str:
        return self._model_name

    def _init_db(self):
        """Initializes SQLite schema for voice biometrics with automatic migration."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS voice_profiles (
                    user_id TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    sample_count INTEGER NOT NULL DEFAULT 1,
                    consistency_score REAL DEFAULT 1.0,
                    session_id TEXT,
                    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_verified_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)
            cursor.execute("PRAGMA table_info(voice_profiles)")
            cols = [col[1] for col in cursor.fetchall()]
            if "consistency_score" not in cols:
                cursor.execute("ALTER TABLE voice_profiles ADD COLUMN consistency_score REAL DEFAULT 1.0")
            if "session_id" not in cols:
                cursor.execute("ALTER TABLE voice_profiles ADD COLUMN session_id TEXT")
            conn.commit()

    def _ensure_ecapa_loaded(self):
        """Loads SpeechBrain ECAPA-TDNN from local model directory or caches it."""
        if SpeakerVerifier._classifier is not None:
            self._model_loaded = True
            return

        try:
            from speechbrain.inference.speaker import EncoderClassifier
            from speechbrain.utils.fetching import LocalStrategy

            if LOCAL_ECAPA_DIR.exists() and (LOCAL_ECAPA_DIR / "hyperparams.yaml").exists():
                # Load directly from local model directory without network
                SpeakerVerifier._classifier = EncoderClassifier.from_hparams(
                    source=str(LOCAL_ECAPA_DIR),
                    savedir=str(LOCAL_ECAPA_DIR),
                    run_opts={"device": self._device},
                )
            else:
                # First-time download using LocalStrategy.COPY for Windows compatibility
                LOCAL_ECAPA_DIR.mkdir(parents=True, exist_ok=True)
                SpeakerVerifier._classifier = EncoderClassifier.from_hparams(
                    source=self._model_name,
                    savedir=str(LOCAL_ECAPA_DIR),
                    run_opts={"device": self._device},
                    local_strategy=LocalStrategy.COPY,
                )

            SpeakerVerifier._model_loaded = True
            SpeakerVerifier._model_load_error = None
        except Exception as e:
            SpeakerVerifier._classifier = None
            SpeakerVerifier._model_loaded = False
            SpeakerVerifier._model_load_error = str(e)

    def extract_embedding(self, audio_float32: np.ndarray) -> np.ndarray:
        """
        Extracts a normalized 192-dimensional speaker embedding vector from 16kHz audio.
        FAILS CLOSED if ECAPA-TDNN is not loaded.
        """
        if not self._model_loaded or SpeakerVerifier._classifier is None:
            raise RuntimeError(
                f"ECAPA-TDNN biometric model is not loaded: {self._model_load_error or 'Model offline'}. "
                "Biometric authentication cannot proceed."
            )

        if len(audio_float32) < 4000:  # Less than 0.25s
            raise ValueError("Audio segment too short for speaker biometric extraction (minimum 0.25s required)")

        tensor = torch.from_numpy(audio_float32).unsqueeze(0)  # Shape [1, T]
        with torch.no_grad():
            embeddings = SpeakerVerifier._classifier.encode_batch(tensor)
            emb_np = embeddings.squeeze().cpu().numpy().astype(np.float32)

        # Ensure 1D 192-dim array
        if emb_np.ndim > 1:
            emb_np = emb_np.squeeze()

        # L2 Normalize
        norm = np.linalg.norm(emb_np)
        if norm > 1e-6:
            emb_np = emb_np / norm
        else:
            raise ValueError("Extracted embedding vector norm is zero")

        return emb_np

    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Computes cosine similarity between two normalized 192-dim embeddings."""
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 < 1e-6 or norm2 < 1e-6:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))

    compute_similarity = cosine_similarity

    def identify_speaker(self, audio_float32: np.ndarray) -> Dict[str, Any]:
        """
        Identifies whether incoming audio matches an enrolled ERPNext speaker profile.
        Returns match status, highest scoring user, similarity score, and threshold.
        """
        if not self._model_loaded:
            return {
                "is_identified": False,
                "user_id": None,
                "score": 0.0,
                "threshold": self.threshold,
                "error": f"ECAPA-TDNN offline: {self._model_load_error}",
                "biometric_engine": self.biometric_engine,
            }

        try:
            incoming_emb = self.extract_embedding(audio_float32)
        except Exception as e:
            return {
                "is_identified": False,
                "user_id": None,
                "score": 0.0,
                "threshold": self.threshold,
                "error": f"Embedding extraction failed: {e}",
                "biometric_engine": self.biometric_engine,
            }

        enrolled = self.get_all_active_profiles()
        if not enrolled:
            return {
                "is_identified": False,
                "user_id": None,
                "score": 0.0,
                "threshold": self.threshold,
                "message": "No voice profiles enrolled in system",
                "biometric_engine": self.biometric_engine,
            }

        # Score against all active profiles
        scored = []
        for user_id, profile_emb in enrolled.items():
            score = self.cosine_similarity(incoming_emb, profile_emb)
            scored.append((user_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        best_user, best_score = scored[0]

        # Check for ambiguity if multiple profiles exist
        is_ambiguous = False
        if len(scored) > 1 and best_score >= self.threshold:
            second_user, second_score = scored[1]
            if (best_score - second_score) < 0.04 and best_user != second_user:
                is_ambiguous = True

        is_identified = bool(best_score >= self.threshold and not is_ambiguous)
        return {
            "is_identified": is_identified,
            "is_ambiguous": is_ambiguous,
            "user_id": best_user if is_identified else None,
            "candidate_user": best_user if best_score >= (self.threshold - 0.05) else None,
            "score": round(float(best_score), 4),
            "threshold": self.threshold,
            "biometric_engine": self.biometric_engine,
            "embedding_dimension": self._embedding_dimension,
        }

    def enroll_speaker(self, user_id: str, audio_samples: List[np.ndarray], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrolls a speaker using up to 5 voice samples.
        Extracts 192-dim ECAPA embeddings for each sample, verifies intra-sample consistency,
        computes the averaged normalized embedding, and saves to voice_profiles.db.
        """
        if not self._model_loaded:
            raise RuntimeError(f"ECAPA-TDNN offline: {self._model_load_error}")

        if not audio_samples or len(audio_samples) < 3:
            raise ValueError("Minimum of 3 voice samples required for enrollment (5 recommended)")

        embeddings = []
        for i, sample in enumerate(audio_samples):
            emb = self.extract_embedding(sample)
            embeddings.append(emb)

        # Compute intra-speaker consistency score across samples
        if len(embeddings) > 1:
            pair_scores = []
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    pair_scores.append(self.cosine_similarity(embeddings[i], embeddings[j]))
            consistency_score = float(np.mean(pair_scores))
            if consistency_score < 0.55:
                raise ValueError(
                    f"Intra-speaker voice consistency score {consistency_score:.2f} is below minimum 0.55. "
                    "Samples sound inconsistent or excessively noisy. Please re-record cleanly."
                )
        else:
            consistency_score = 1.0

        # Mean normalized embedding across all samples
        mean_emb = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(mean_emb)
        if norm > 1e-6:
            mean_emb = mean_emb / norm

        # Save to database
        emb_bytes = mean_emb.astype(np.float32).tobytes()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO voice_profiles (user_id, embedding, sample_count, consistency_score, session_id, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    embedding = excluded.embedding,
                    sample_count = excluded.sample_count,
                    consistency_score = excluded.consistency_score,
                    session_id = COALESCE(excluded.session_id, voice_profiles.session_id),
                    enrolled_at = CURRENT_TIMESTAMP,
                    is_active = 1
            """, (user_id, emb_bytes, len(audio_samples), consistency_score, session_id))
            conn.commit()

        return {
            "success": True,
            "user_id": user_id,
            "samples_enrolled": len(audio_samples),
            "consistency_score": round(consistency_score, 4),
            "similarity_threshold": self.threshold,
            "embedding_dimension": self._embedding_dimension,
            "biometric_engine": self.biometric_engine,
        }

    enroll_voice_profile = enroll_speaker

    def update_user_session(self, user_id: str, session_id: str):
        """Updates the active Frappe session ID (sid) associated with an enrolled user."""
        if not user_id or not session_id:
            return
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE voice_profiles SET session_id = ?, last_verified_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (session_id.strip(), user_id.strip()),
            )
            conn.commit()

    def get_user_session(self, user_id: str) -> Optional[str]:
        """Retrieves stored Frappe session ID (sid) for an enrolled user."""
        if not user_id:
            return None
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM voice_profiles WHERE user_id = ? AND is_active = 1", (user_id.strip(),))
            row = cursor.fetchone()
            if row and row[0]:
                return row[0]
        return None

    def get_all_active_profiles(self) -> Dict[str, np.ndarray]:
        """Retrieves all active enrolled speaker embeddings from database."""
        profiles = {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, embedding FROM voice_profiles WHERE is_active = 1")
            for user_id, blob in cursor.fetchall():
                emb = np.frombuffer(blob, dtype=np.float32)
                profiles[user_id] = emb
        return profiles

    def list_enrolled_users(self) -> List[str]:
        """Lists user IDs of enrolled profiles."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM voice_profiles WHERE is_active = 1")
            return [row[0] for row in cursor.fetchall()]

    def delete_profile(self, user_id: str) -> bool:
        """Deactivates a user's voice profile."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM voice_profiles WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
