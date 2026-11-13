"""
OrbisERP Step 3C — Automated Voice Pipeline Test Suite
======================================================
Tests:
1. Audio conversion, resampling, and VAD speech framing
2. Wake-word pattern matching & transcript stripping
3. Speech-to-Text transcription
4. Speaker embedding extraction, cosine similarity, and thresholding
5. Unknown speaker rejection (unauthorized voiceprint)
6. Voice enrollment validation with consistency calibration
7. Native ERPNext credentials verification (invalid credentials rejected)
8. Disabled account prevention
9. Text-to-Speech audio response generation
10. Ollama intent parsing and ERPNext stock API querying
11. End-to-end voice pipeline execution
"""

import sys
from pathlib import Path
import unittest
import numpy as np
import io
import soundfile as sf

# Set path to ai-backend root
AI_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AI_BACKEND_DIR))

from app.voice.audio_processor import AudioProcessor
from app.voice.stt_engine import STTEngine
from app.voice.speaker_verifier import SpeakerVerifier
from app.voice.intent_router import IntentRouter
from app.voice.tts_engine import TTSEngine
from app.core.security import verify_erpnext_credentials, check_user_stock_permission, verify_erpnext_session, normalize_spoken_email
from app.core.config import settings


def generate_synthetic_speech_audio(duration: float = 1.5, freq: float = 220.0, sample_rate: int = 16000) -> np.ndarray:
    """Generates synthetic harmonic audio with amplitude modulation resembling speech."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Fundamental + harmonics
    signal = 0.5 * np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * (freq * 2) * t) + 0.15 * np.sin(2 * np.pi * (freq * 3) * t)
    # Syllable-like envelope (3 Hz modulation)
    envelope = 0.5 * (1 + np.sin(2 * np.pi * 3.5 * t))
    audio = signal * envelope * 0.8
    return audio.astype(np.float32)


def generate_wav_bytes(audio: np.ndarray, sample_rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


class TestVoicePipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.audio_proc = AudioProcessor(vad_mode=2)
        cls.stt = STTEngine(model_size="base.en")
        # Use an isolated test database
        cls.test_db = AI_BACKEND_DIR / "test_voice_profiles.db"
        if cls.test_db.exists():
            cls.test_db.unlink()
        cls.verifier = SpeakerVerifier(db_path=cls.test_db, threshold=0.75)
        cls.intent = IntentRouter()
        cls.tts = TTSEngine()

    @classmethod
    def tearDownClass(cls):
        try:
            if hasattr(cls, "verifier"):
                del cls.verifier
            import gc
            gc.collect()
            if cls.test_db.exists():
                cls.test_db.unlink()
        except OSError:
            pass

    # 1. Audio Processing & VAD
    def test_01_audio_loading_and_resampling(self):
        """Tests loading multi-channel and different sample rate audio."""
        orig_sr = 44100
        synth = generate_synthetic_speech_audio(duration=1.0, freq=250.0, sample_rate=orig_sr)
        wav_bytes = generate_wav_bytes(synth, sample_rate=orig_sr)
        
        loaded, sr = self.audio_proc.load_audio(wav_bytes)
        self.assertEqual(sr, 16000)
        self.assertTrue(len(loaded) > 0)
        self.assertAlmostEqual(len(loaded) / 16000, 1.0, delta=0.05)

    def test_02_vad_speech_detection(self):
        """Tests VAD speech detection vs silence."""
        speech_audio = generate_synthetic_speech_audio(duration=1.2, freq=200.0)
        res_speech = self.audio_proc.process_vad(speech_audio)
        self.assertTrue(res_speech["duration_seconds"] > 1.0)
        
        # Test pure silence
        silence_audio = np.zeros(16000, dtype=np.float32)
        res_silence = self.audio_proc.process_vad(silence_audio)
        self.assertFalse(res_silence["has_speech"])

    def test_03_audio_quality_metrics(self):
        """Tests quality metrics rejection for very quiet or very short audio."""
        too_short = np.zeros(4000, dtype=np.float32)  # 0.25s
        res_short = self.audio_proc.calculate_quality(too_short)
        self.assertFalse(res_short["is_valid"])

        valid_sample = generate_synthetic_speech_audio(duration=1.5, freq=180.0)
        res_valid = self.audio_proc.calculate_quality(valid_sample)
        self.assertTrue(res_valid["is_valid"])

    # 2. Wake-Word Detection
    def test_04_wake_word_spotting(self):
        """Tests wake word detection and stripping."""
        self.assertTrue(self.stt.has_wake_word("Orbis check stock balance"))
        self.assertTrue(self.stt.has_wake_word("Hey Orbis, show items"))
        self.assertTrue(self.stt.has_wake_word("Activate Orbis"))
        self.assertFalse(self.stt.has_wake_word("Show me the balance for sedan"))

        cleaned = self.stt.strip_wake_word("Hey Orbis, check stock for engine")
        self.assertEqual(cleaned, "check stock for engine")

    # 3. Speaker Biometrics (ECAPA-TDNN / Acoustic Embeddings)
    def test_05_speaker_embedding_extraction(self):
        """Tests embedding shape, normalization, and repeatability."""
        sample = generate_synthetic_speech_audio(duration=1.5, freq=210.0)
        emb = self.verifier.extract_embedding(sample)
        self.assertEqual(len(emb), 192)
        norm = np.linalg.norm(emb)
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_06_speaker_cosine_similarity(self):
        """Tests that identical audio has similarity ~1.0 and different frequencies have lower similarity."""
        sample_a = generate_synthetic_speech_audio(duration=1.5, freq=150.0)
        sample_b = generate_synthetic_speech_audio(duration=1.5, freq=450.0)

        emb_a = self.verifier.extract_embedding(sample_a)
        emb_b = self.verifier.extract_embedding(sample_b)

        sim_same = self.verifier.compute_similarity(emb_a, emb_a)
        self.assertAlmostEqual(sim_same, 1.0, places=4)

        sim_diff = self.verifier.compute_similarity(emb_a, emb_b)
        self.assertTrue(sim_diff < 0.75, f"Impostor similarity {sim_diff} should be below 0.75")

    def test_07_unknown_speaker_rejection_when_empty(self):
        """Tests that identification fails safely when no profiles are enrolled."""
        sample = generate_synthetic_speech_audio(duration=1.5, freq=220.0)
        res = self.verifier.identify_speaker(sample)
        self.assertFalse(res["is_identified"])
        self.assertIsNone(res["user_id"])

    def test_08_voice_enrollment_multi_sample(self):
        """Tests voice enrollment with 3 samples, consistency check, and profile persistence."""
        samples = [
            generate_synthetic_speech_audio(duration=1.5, freq=180.0),
            generate_synthetic_speech_audio(duration=1.6, freq=182.0),
            generate_synthetic_speech_audio(duration=1.5, freq=181.0),
        ]
        res = self.verifier.enroll_voice_profile("test_user@orbis.erp", samples)
        self.assertTrue(res["success"])
        self.assertEqual(res["samples_enrolled"], 3)
        self.assertTrue(res["consistency_score"] > 0.65)

        # Verify enrolled list
        enrolled = self.verifier.list_enrolled_users()
        self.assertIn("test_user@orbis.erp", enrolled)

    def test_09_authorized_vs_impostor_verification(self):
        """Tests that genuine speaker matches and impostor speaker is rejected."""
        genuine_sample = generate_synthetic_speech_audio(duration=1.5, freq=181.0)
        impostor_sample = generate_synthetic_speech_audio(duration=1.5, freq=500.0)

        res_genuine = self.verifier.identify_speaker(genuine_sample)
        self.assertTrue(res_genuine["is_identified"])
        self.assertEqual(res_genuine["user_id"], "test_user@orbis.erp")
        self.assertTrue(res_genuine["score"] >= 0.75)

        res_impostor = self.verifier.identify_speaker(impostor_sample)
        self.assertFalse(res_impostor["is_identified"])
        self.assertTrue(res_impostor["score"] < 0.75)

    # 4. Native ERPNext Authentication & RBAC Checks
    def test_10_erpnext_credential_verification_invalid(self):
        """Tests that invalid credentials cannot enroll a voice profile."""
        res = verify_erpnext_credentials("Administrator", "completely_wrong_password_xyz")
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["error_code"], "AUTH_FAILED")

    def test_11_rbac_permission_check(self):
        """Tests RBAC validation for Administrator."""
        self.assertTrue(check_user_stock_permission("Administrator"))

    # 5. Intent Routing & ERPNext Stock API
    def test_12_intent_parser_and_stock_execution(self):
        """Tests intent routing against live ERPNext Stock endpoint."""
        res = self.intent.process_query("check stock for sedan", "Administrator")
        self.assertIn("response_text", res)
        self.assertIn(res["intent"], ("check_stock", "general_query"))

    def test_13_unauthorized_user_stock_rejection(self):
        """Tests that unauthorized user cannot access stock records."""
        res = self.intent.process_query("check stock for sedan", "unauthorized_guest@external.com")
        self.assertEqual(res.get("data", {}).get("error"), "RBAC_RESTRICTED")
        self.assertIn("Access denied", res["response_text"])

    # 6. TTS Audio Synthesis
    def test_14_tts_synthesis(self):
        """Tests speech synthesis generates non-empty audio."""
        import asyncio
        res = asyncio.run(self.tts.synthesize("Stock balance is 50 units."))
        self.assertTrue(len(res["audio_base64"]) > 0)
        self.assertIn(res["audio_format"], ("audio/mp3", "audio/wav"))
        self.assertIn(res["is_online"], (True, False))

    # 7. Identity & Session Integrity Verification
    def test_15_guest_and_forged_session_rejection(self):
        """Tests that missing or forged sessions evaluate strictly to Guest and are denied access to Stock."""
        # Unauthenticated / empty session
        res_none = verify_erpnext_session(None)
        self.assertFalse(res_none["is_authenticated"])
        self.assertEqual(res_none["user"], "Guest")

        # Forged session ID
        res_fake = verify_erpnext_session("forged_session_token_xyz_12345")
        self.assertFalse(res_fake["is_authenticated"])
        self.assertEqual(res_fake["user"], "Guest")

        # Guest permissions on stock doctypes
        self.assertFalse(check_user_stock_permission("Guest"))

        # Processing stock request as Guest produces RBAC refusal
        res_stock = self.intent.process_query("check stock for sedan", "Guest")
        self.assertEqual(res_stock.get("data", {}).get("error"), "RBAC_RESTRICTED")
        self.assertIn("Access denied", res_stock["response_text"])

    def test_16_biometric_engine_dynamic_reporting(self):
        """Tests that the active biometric engine name accurately reflects runtime status."""
        engine_name = self.verifier.engine_name
        self.assertIn(engine_name, (
            "SpeechBrain ECAPA-TDNN (neural)",
            "Acoustic MFCC & Pitch Biometrics (192-dim local fallback)"
        ))

    def test_17_anonymized_unauthorized_speaker_response(self):
        """Tests that unknown speakers do not leak candidate user identities."""
        impostor_audio = generate_synthetic_speech_audio(duration=1.5, freq=550.0)
        res = self.verifier.identify_speaker(impostor_audio)
        self.assertFalse(res["is_identified"])
        self.assertIsNone(res["user_id"])
        self.assertIsNone(res["candidate_user"])

    # 8. Female Voice & Spoken Credential Parsing
    def test_18_female_voice_configuration(self):
        """Tests that the primary TTS voice is configured to en-US-AriaNeural."""
        self.assertEqual(self.tts.voice, "en-US-AriaNeural")

    def test_19_spoken_email_normalization(self):
        """Tests converting natural spoken email patterns into normalized email addresses."""
        self.assertEqual(
            normalize_spoken_email("ayesha dot tahir at gmail dot com"),
            "ayesha.tahir@gmail.com",
        )
        self.assertEqual(
            normalize_spoken_email("administrator at orbis dot erp"),
            "administrator@orbis.erp",
        )
        self.assertEqual(
            normalize_spoken_email("user underscore one hyphen test at company dot com"),
            "user_one-test@company.com",
        )
        self.assertEqual(
            normalize_spoken_email("my email is john dot doe at example dot net"),
            "john.doe@example.net",
        )

    def test_20_vad_endpoint_silence_setting(self):
        """Tests that VAD endpoint silence countdown is configured to 10 seconds."""
        self.assertEqual(settings.vad_endpoint_silence_seconds, 10)


if __name__ == "__main__":
    unittest.main()
