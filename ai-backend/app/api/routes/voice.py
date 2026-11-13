"""
OrbisERP AI Layer — Voice Pipeline REST Endpoints
=================================================
Provides complete end-to-end processing:
Wake Word -> VAD -> STT -> Speaker Verification -> Intent Routing -> ERPNext API -> TTS.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
import io
import re

from app.core.config import settings
from app.core.security import (
    verify_erpnext_credentials,
    verify_erpnext_session,
    normalize_spoken_email,
    check_erpnext_user_exists,
)
from app.voice.audio_processor import AudioProcessor
from app.voice.stt_engine import STTEngine
from app.voice.speaker_verifier import SpeakerVerifier
from app.voice.intent_router import IntentRouter
from app.voice.tts_engine import TTSEngine

router = APIRouter(prefix="/voice", tags=["Voice Pipeline"])

# Singleton instances for CPU efficiency
audio_proc = AudioProcessor(vad_mode=2)
stt_engine = STTEngine(model_size="base.en")
speaker_verifier = SpeakerVerifier()
intent_router = IntentRouter()
tts_engine = TTSEngine()


class TextQueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None  # Frappe session cookie (sid)


class ParseEmailRequest(BaseModel):
    spoken_text: str


class VerifyCredentialsRequest(BaseModel):
    user_id: str
    password: str


@router.post("/detect-wake-word", summary="Local Wake-Word Detection on Audio Chunk")
async def detect_wake_word(audio: UploadFile = File(...)):
    """
    Analyzes an audio slice from client microphone to spot the wake word 'Orbis'.
    Runs 100% locally via faster-whisper without external network dependencies.
    """
    raw_bytes = await audio.read()
    if not raw_bytes:
        return {"wake_word_detected": False, "transcript": ""}

    try:
        audio_float32, _ = audio_proc.load_audio(raw_bytes)
        stt_result = stt_engine.transcribe(audio_float32)
        has_wake = stt_result["has_wake_word"]
        return {
            "wake_word_detected": has_wake,
            "transcript": stt_result["text"],
            "clean_query": stt_result["clean_query"],
        }
    except Exception as e:
        return {"wake_word_detected": False, "error": str(e), "transcript": ""}


@router.post("/dictate-email", summary="Voice Email Dictation from Audio Stream")
async def dictate_email(audio: UploadFile = File(...)):
    """
    Processes audio of a user speaking their email address (e.g. 'ayesha dot tahir at gmail dot com').
    Transcribes locally with faster-whisper, normalizes symbols, checks ERPNext account existence,
    and synthesizes a female voice confirmation audio.
    """
    raw_bytes = await audio.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Empty audio buffer")

    audio_float32, _ = audio_proc.load_audio(raw_bytes)
    stt_res = stt_engine.transcribe(audio_float32)
    raw_spoken = stt_res["text"]

    normalized_email = normalize_spoken_email(raw_spoken)
    is_valid_format = bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized_email))

    user_info = check_erpnext_user_exists(normalized_email) if is_valid_format else {"exists": False, "is_enabled": False, "full_name": None}

    if is_valid_format and user_info["exists"] and user_info["is_enabled"]:
        spoken_msg = f"I understood your email as {normalized_email}. Is this email address correct?"
    elif is_valid_format and user_info["exists"] and not user_info["is_enabled"]:
        spoken_msg = f"The account for {normalized_email} is currently disabled in ERPNext. Please contact your system administrator."
    elif is_valid_format and not user_info["exists"]:
        spoken_msg = f"The email {normalized_email} was not found in ERPNext. Please check the spelling or register first."
    else:
        spoken_msg = f"I heard '{raw_spoken}'. Please clearly dictate your registered email, for example, user dot name at company dot com."

    tts = await tts_engine.synthesize(spoken_msg)
    return {
        "status": "success",
        "raw_transcript": raw_spoken,
        "interpreted_email": normalized_email,
        "is_valid_format": is_valid_format,
        "user_exists": user_info["exists"],
        "is_enabled": user_info["is_enabled"],
        "full_name": user_info.get("full_name"),
        "response_text": spoken_msg,
        "audio_base64": tts["audio_base64"],
        "audio_format": tts["audio_format"],
    }


@router.post("/parse-email", summary="Parse and Validate Spoken Email Text")
async def parse_email_endpoint(req: ParseEmailRequest):
    """
    Parses spoken email dictation text, validates format, checks ERPNext existence,
    and returns female TTS confirmation audio.
    """
    raw_email = normalize_spoken_email(req.spoken_text)
    is_valid_format = bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", raw_email))
    user_info = check_erpnext_user_exists(raw_email) if is_valid_format else {"exists": False, "is_enabled": False, "full_name": None}

    if is_valid_format and user_info["exists"] and user_info["is_enabled"]:
        spoken_msg = f"I understood your email as {raw_email}. Is this email address correct?"
    elif is_valid_format and user_info["exists"] and not user_info["is_enabled"]:
        spoken_msg = f"The account for {raw_email} is currently disabled in ERPNext. Please contact your system administrator."
    elif is_valid_format and not user_info["exists"]:
        spoken_msg = f"The email {raw_email} was not found in ERPNext. Please confirm your registered account."
    else:
        spoken_msg = f"I could not clearly understand the email from '{req.spoken_text}'. Please state your email clearly."

    tts = await tts_engine.synthesize(spoken_msg)
    return {
        "status": "success",
        "interpreted_email": raw_email,
        "is_valid_format": is_valid_format,
        "user_exists": user_info["exists"],
        "is_enabled": user_info["is_enabled"],
        "full_name": user_info.get("full_name"),
        "response_text": spoken_msg,
        "audio_base64": tts["audio_base64"],
        "audio_format": tts["audio_format"],
    }


@router.post("/verify-credentials", summary="Secure Server-Side Credential Verification")
async def verify_credentials_endpoint(req: VerifyCredentialsRequest):
    """
    Verifies user credentials directly against Frappe without storing the password.
    Returns authentic Frappe session ID (sid) for session establishment and voice enrollment.
    """
    auth_check = verify_erpnext_credentials(req.user_id, req.password)
    if not auth_check["is_valid"]:
        error_msg = auth_check.get("reason", "Invalid ERPNext username or password")
        tts = await tts_engine.synthesize(error_msg)
        return {
            "status": "failed",
            "is_valid": False,
            "reason": error_msg,
            "response_text": error_msg,
            "audio_base64": tts["audio_base64"],
            "audio_format": tts["audio_format"],
        }

    target_user_id = auth_check.get("user_id", req.user_id)
    if auth_check.get("session_id"):
        speaker_verifier.update_user_session(target_user_id, auth_check["session_id"])

    success_msg = f"Credentials verified for {auth_check['full_name']}. Please record five separate voice samples to complete enrollment."
    tts = await tts_engine.synthesize(success_msg)
    return {
        "status": "success",
        "is_valid": True,
        "user_id": target_user_id,
        "full_name": auth_check["full_name"],
        "session_id": auth_check.get("session_id"),
        "response_text": success_msg,
        "audio_base64": tts["audio_base64"],
        "audio_format": tts["audio_format"],
    }


@router.post("/enroll", summary="First-Time Voice Enrollment with ERPNext Verification (5 Samples)")
async def enroll_voice(
    user_id: str = Form(...),
    password: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    sample1: UploadFile = File(...),
    sample2: UploadFile = File(...),
    sample3: UploadFile = File(...),
    sample4: Optional[UploadFile] = File(None),
    sample5: Optional[UploadFile] = File(None),
):
    """
    Enrolls a speaker voiceprint associated strictly with an existing, enabled ERPNext user.
    Uses SpeechBrain ECAPA-TDNN to extract 192-dimensional embeddings from up to 5 samples.
    Fails closed if ECAPA-TDNN is offline.
    """
    if not speaker_verifier.model_loaded:
        raise HTTPException(
            status_code=500,
            detail=f"Biometric engine offline: {speaker_verifier.model_load_error}",
        )

    # 1. Verify credentials if password supplied, or verify user exists
    if password:
        auth_check = verify_erpnext_credentials(user_id, password)
        if not auth_check["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=auth_check["reason"],
            )
        full_name = auth_check["full_name"]
        target_user_id = auth_check.get("user_id", user_id)
    else:
        user_info = check_erpnext_user_exists(user_id)
        if not user_info["exists"] or not user_info["is_enabled"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account does not exist or is disabled in ERPNext.",
            )
        full_name = user_info["full_name"]
        target_user_id = user_info.get("canonical_user_id", user_id)

    # 2. Decode and Validate Audio Samples (up to 5)
    upload_list = [sample1, sample2, sample3]
    if sample4 is not None:
        upload_list.append(sample4)
    if sample5 is not None:
        upload_list.append(sample5)

    processed_samples = []
    for i, file_obj in enumerate(upload_list):
        raw_bytes = await file_obj.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail=f"Voice sample {i+1} is empty")
        try:
            audio_f32, _ = audio_proc.load_audio(raw_bytes)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Sample {i+1} decoding failed: {e}")

        # Quality check
        quality = audio_proc.calculate_quality(audio_f32)
        if not quality["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Sample {i+1} failed quality check: {quality['reason']}",
            )

        # Silero VAD trim
        vad_res = audio_proc.process_vad(audio_f32)
        trimmed = vad_res["trimmed_audio"] if vad_res["has_speech"] else audio_f32
        processed_samples.append(trimmed)

    # 3. Enroll in SQLite using SpeechBrain ECAPA-TDNN
    try:
        active_sid = auth_check.get("session_id") if password else session_id
        enrollment_result = speaker_verifier.enroll_speaker(target_user_id, processed_samples, session_id=active_sid)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ECAPA-TDNN enrollment failed: {e}",
        )

    welcome_msg = (
        f"Voice enrollment successfully completed for {full_name}. "
        f"Your biometric profile has been calibrated with {len(processed_samples)} samples. "
        "Welcome to Orbis ERP."
    )
    tts = await tts_engine.synthesize(welcome_msg)

    return {
        "status": "success",
        "user_id": target_user_id,
        "input_user": user_id,
        "full_name": full_name,
        "samples_enrolled": len(processed_samples),
        "consistency_score": enrollment_result["consistency_score"],
        "threshold": enrollment_result["similarity_threshold"],
        "embedding_dimension": enrollment_result["embedding_dimension"],
        "biometric_engine": enrollment_result["biometric_engine"],
        "welcome_message": welcome_msg,
        "audio_base64": tts["audio_base64"],
        "audio_format": tts["audio_format"],
    }


@router.post("/process", summary="Process Audio Stream / Utterance")
async def process_voice(
    audio: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    session_id: Optional[str] = Form(None),
    manual_trigger: bool = Form(False),
    wake_word_verified: bool = Form(False),
):
    """
    Executes full Orbis Voice Pipeline:
    1. Audio format decoding & 16kHz resampling
    2. Silero neural Voice Activity Detection (VAD)
    3. faster-whisper STT & Wake-word spotter
    4. SpeechBrain ECAPA-TDNN Speaker Biometric Verification
    5. Intent Parsing & RBAC-enforced ERPNext execution
    6. TTS Response synthesis (text & female audio returned separately)
    """
    upload = audio or file
    if upload is None:
        raise HTTPException(
            status_code=422,
            detail="Missing audio payload. Please provide audio in 'audio' or 'file' form-data field.",
        )

    audio_bytes = await upload.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    # 1. Decode & Resample to 16kHz float32
    try:
        audio_float32, sr = audio_proc.load_audio(audio_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Audio decoding error: {e}")

    # 2. VAD - Voice Activity Detection
    vad_result = audio_proc.process_vad(audio_float32)
    if not vad_result["has_speech"]:
        tts = await tts_engine.synthesize("No speech detected.")
        return {
            "status": "no_speech",
            "transcript": "",
            "response_text": "No speech detected. Please speak clearly into your microphone.",
            "audio_base64": tts["audio_base64"],
            "audio_format": tts["audio_format"],
        }

    trimmed_audio = vad_result["trimmed_audio"]

    # 3. STT Transcription & Wake Word Detection
    stt_result = stt_engine.transcribe(trimmed_audio)
    full_text = stt_result["text"]
    clean_query = stt_result["clean_query"]
    has_wake_word = stt_result["has_wake_word"]

    # Enforce wake word requirement unless manually clicked or verified by wake-word trigger
    if not manual_trigger and not wake_word_verified and not has_wake_word:
        return {
            "status": "wake_word_required",
            "transcript": full_text,
            "response_text": "Please say 'Orbis' to activate the assistant.",
            "audio_base64": "",
            "audio_format": "audio/wav",
            "speaker": {"is_identified": False},
        }

    # If query was just the wake word (e.g. "Orbis")
    if not clean_query:
        tts = await tts_engine.synthesize("Hello! I'm listening. How can I help you?")
        return {
            "status": "wake_word_activated",
            "transcript": full_text,
            "response_text": "Hello! I'm listening. How can I help you with Orbis ERP?",
            "audio_base64": tts["audio_base64"],
            "audio_format": tts["audio_format"],
            "speaker": {"is_identified": False},
        }

    # 4. Speaker Identification & Voice Biometrics via SpeechBrain ECAPA-TDNN
    speaker_result = speaker_verifier.identify_speaker(trimmed_audio)
    enrolled_users = speaker_verifier.list_enrolled_users()

    # If no voice profiles are enrolled yet, guide user to first-time enrollment
    if not enrolled_users:
        spoken = "Welcome to Orbis. No voice profiles are enrolled yet. Please complete first-time enrollment to connect your ERPNext account."
        tts = await tts_engine.synthesize(spoken)
        return {
            "status": "enrollment_required",
            "transcript": full_text,
            "response_text": spoken,
            "audio_base64": tts["audio_base64"],
            "audio_format": tts["audio_format"],
            "speaker": speaker_result,
        }

    # If multiple close profiles detected
    if speaker_result.get("is_ambiguous"):
        spoken = "Multiple speaker profiles closely matched your voice. Additional verification is required. Access denied."
        tts = await tts_engine.synthesize("Voice match is ambiguous. Access to ERPNext is denied.")
        return {
            "status": "ambiguous_speaker",
            "transcript": full_text,
            "response_text": spoken,
            "audio_base64": tts["audio_base64"],
            "audio_format": tts["audio_format"],
            "speaker": speaker_result,
        }

    # If speaker does not match enrolled profile with threshold >= calibrated threshold
    if not speaker_result["is_identified"]:
        score_val = speaker_result.get('score', 0.0)
        thresh_val = speaker_result.get('threshold', 0.75)
        spoken = f"Speaker verification failed. Voice similarity score {score_val:.2f} is below the authorized threshold of {thresh_val:.2f}. Access denied."
        tts = await tts_engine.synthesize("Speaker not recognized. Access to ERPNext is denied.")
        return {
            "status": "unauthorized_speaker",
            "transcript": full_text,
            "response_text": spoken,
            "audio_base64": tts["audio_base64"],
            "audio_format": tts["audio_format"],
            "speaker": speaker_result,
        }

    authenticated_user = speaker_result["user_id"]

    # 5. Intent Processing & ERPNext REST Execution (Authenticated & RBAC Checked)
    execution_result = intent_router.process_query(clean_query, authenticated_user, session_id=session_id)
    response_text = execution_result["response_text"]

    # 6. Text-to-Speech Synthesis
    tts_result = await tts_engine.synthesize(response_text)

    return {
        "status": "success",
        "transcript": full_text,
        "clean_query": clean_query,
        "authenticated_user": authenticated_user,
        "speaker": speaker_result,
        "intent": execution_result["intent"],
        "erp_data": execution_result.get("data"),
        "response_text": response_text,
        "audio_base64": tts_result["audio_base64"],
        "audio_format": tts_result["audio_format"],
        "tts_engine": tts_result["engine"],
    }


@router.post("/text-query", summary="Execute Text Query (Portal Input Bar)")
async def execute_text_query(req: TextQueryRequest):
    """
    Handles text queries submitted through the portal's bottom input bar.
    Strictly verifies identity via ERPNext session (Frappe sid).
    Never trusts client-supplied user IDs without cryptographic session validation.
    Applies RBAC checks and returns both text and speech audio.
    """
    session_info = verify_erpnext_session(req.session_id)
    authenticated_user = session_info["user"]

    execution = intent_router.process_query(req.query, authenticated_user, session_id=req.session_id)
    response_text = execution["response_text"]
    tts = await tts_engine.synthesize(response_text)

    return {
        "status": "success",
        "query": req.query,
        "user_id": authenticated_user,
        "is_authenticated": session_info["is_authenticated"],
        "intent": execution["intent"],
        "data": execution.get("data"),
        "response_text": response_text,
        "audio_base64": tts["audio_base64"],
        "audio_format": tts["audio_format"],
        "tts_engine": tts["engine"],
    }


@router.get("/status", summary="Voice Pipeline Diagnostic Status")
async def voice_status():
    """Returns exact diagnostic status of all functional layers (ECAPA, VAD, STT, TTS, Enrolled, DSPy)."""
    enrolled = speaker_verifier.list_enrolled_users()
    from app.ai.dspy_config import DSPyConfigManager
    return {
        "pipeline_status": "operational",
        "reasoning_engine": "DSPy 3.4.1 (Signatures, Modules & Live ERPNext Tools)",
        "llm_provider_mode": settings.llm_provider,
        "active_llm_provider": DSPyConfigManager.active_provider(),
        "groq_model": settings.groq_model,
        "ollama_model": settings.ollama_model,
        "wake_word": "Orbis",
        "wake_word_engine": "faster-whisper local audio chunk spotter + client phonetic accelerator",
        "vad_engine": audio_proc.vad_engine,
        "vad_endpoint_silence_seconds": settings.vad_endpoint_silence_seconds,
        "stt_engine": "faster-whisper (CPU int8)",
        "biometric_engine": speaker_verifier.biometric_engine,
        "model_loaded": speaker_verifier.model_loaded,
        "model_name": speaker_verifier.model_name,
        "embedding_dimension": speaker_verifier.embedding_dimension,
        "device": speaker_verifier.device,
        "model_load_error": speaker_verifier.model_load_error,
        "similarity_threshold": speaker_verifier.threshold,
        "enrolled_users_count": len(enrolled),
        "enrolled_users": enrolled,
        "tts_engine": f"Edge TTS ({tts_engine.voice}) [cloud-assisted Microsoft Neural]",
    }
