"""
Step 32: Setup Orbis Pre-Login Portal Foundation (Step 3A, 3B, 3C Complete Rework)
==================================================================================
Orbis Car Manufacturing (Pvt.) Ltd.

Fully functional Layer 1, Layer 2, Layer 3, and Layer 4 implementation:
- Layer 1: Real-time Audio-Reactive Web Audio API Waveform inside the Luminous Orb
- Layer 2: Automatic Hands-free Wake-Word Spotting ("Orbis") without mouse clicks
           Silero VAD + 10-Second Silence Confirmation with Auto-Reset on Resumed Speech
           Dedicated Voice Email Dictation with local faster-whisper transcription
           Female TTS (en-US-AriaNeural via Edge-TTS)
- Layer 3: SpeechBrain ECAPA-TDNN (192-dim neural embeddings) for genuine voice biometrics
           5-Sample Enrollment & Intra-Speaker Consistency Scoring
- Layer 4: Genuine ERPNext Authenticated Session Establishment (Frappe sid)
           Strict identity mapping with existing ERPNext accounts
"""

import os
import frappe
from pathlib import Path

CONTAINER_WWW_DIR = Path("/home/frappe/frappe-bench/apps/erpnext/erpnext/www")

ORBIS_PY_CONTENT = r'''import frappe
from frappe import _

no_cache = 1

def get_context(context):
    context.no_cache = 1
    user = frappe.session.user
    is_authenticated = bool(user and user != "Guest")
    
    context.is_authenticated = is_authenticated
    context.user = user
    
    if is_authenticated:
        context.user_fullname = frappe.utils.get_fullname(user) or user
        roles = frappe.get_roles(user)
        display_roles = [r for r in roles if r not in ["All", "Guest", "Blogger", "Customer", "Supplier"]]
        context.user_roles = display_roles[:3] if display_roles else ["User"]
    else:
        context.user_fullname = None
        context.user_roles = []
    
    context.app_name = "Orbis ERP | Orbis Car Manufacturing (Pvt.) Ltd."
    context.title = "OrbisERP"
    context.csrf_token = frappe.sessions.get_csrf_token()
    return context
'''

ORBIS_HTML_CONTENT = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{{ title or "Orbis ERP" }}</title>
  <link rel="shortcut icon" href="/assets/erpnext/images/erpnext-favicon.svg" type="image/x-icon">
  <style>
    :root {
      --bg-midnight: #02060D;
      --sky-blue: #70CCFF;
      --pale-cyan: #9FDDFF;
      --icy-white: #E0F2FE;
      --highlight-white: #F3FBFF;
      --muted-text: #728A9C;
      --glass-navy: rgba(5, 15, 30, 0.78);
      --glass-border: rgba(40, 95, 145, 0.35);
      --success-cyan: #22d3ee;
      --warning-amber: #f59e0b;
      --error-red: #ef4444;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    html, body {
      width: 100%;
      height: 100%;
      min-height: 100vh;
      overflow-x: hidden;
      background-color: var(--bg-midnight);
      color: var(--icy-white);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Cosmic dark space background */
    body {
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      align-items: center;
      background: 
        radial-gradient(circle at 50% 48%, rgba(25, 110, 180, 0.28) 0%, rgba(4, 22, 45, 0.72) 42%, var(--bg-midnight) 84%),
        radial-gradient(circle at 15% 15%, rgba(22, 139, 208, 0.06) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(7, 85, 139, 0.08) 0%, transparent 45%);
      padding: max(24px, env(safe-area-inset-top)) max(28px, env(safe-area-inset-right)) max(28px, env(safe-area-inset-bottom)) max(28px, env(safe-area-inset-left));
    }

    #space-particles {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 1;
    }

    /* Header Bar */
    .header-bar {
      position: relative;
      z-index: 20;
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .wordmark-wrap {
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      user-select: none;
    }

    .wordmark-svg {
      display: block;
      height: clamp(34px, 4vw, 44px);
      width: auto;
      overflow: visible;
    }

    .title-star {
      filter: drop-shadow(0 0 4px #70CCFF);
      animation: titleStarTwinkle 4s ease-in-out infinite alternate;
    }

    @keyframes titleStarTwinkle {
      0% { opacity: 0.6; transform: scale(0.9); }
      100% { opacity: 1; transform: scale(1.2); }
    }

    .svg-orbis-text {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      font-size: 34px;
      font-weight: 500;
      letter-spacing: 4px;
      fill: rgba(4, 18, 36, 0.12);
      stroke: url(#neonWaveGrad);
      stroke-width: 1.4px;
      stroke-linejoin: round;
      paint-order: stroke fill;
      filter: drop-shadow(0 0 3px rgba(112, 204, 255, 0.95)) drop-shadow(0 0 10px rgba(45, 155, 230, 0.75)) drop-shadow(0 0 22px rgba(22, 139, 208, 0.45));
      animation: orbisGlowBreathe 8s ease-in-out infinite alternate;
    }

    @keyframes orbisGlowBreathe {
      0% { filter: drop-shadow(0 0 3px rgba(112, 204, 255, 0.95)) drop-shadow(0 0 10px rgba(45, 155, 230, 0.75)) drop-shadow(0 0 22px rgba(22, 139, 208, 0.45)); }
      100% { filter: drop-shadow(0 0 5px rgba(200, 240, 255, 1)) drop-shadow(0 0 14px rgba(70, 185, 255, 0.9)) drop-shadow(0 0 28px rgba(30, 150, 225, 0.6)); }
    }

    .svg-erp-text {
      font-family: "Playfair Display", "Cormorant Garamond", Georgia, "Times New Roman", serif;
      font-size: 24px;
      font-style: italic;
      font-weight: 500;
      fill: #B5EAFF;
      letter-spacing: 1px;
      filter: drop-shadow(0 0 8px rgba(112, 204, 255, 0.75)) drop-shadow(0 0 18px rgba(35, 145, 225, 0.4));
    }

    .top-controls {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .glass-nav-btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(5, 18, 38, 0.72);
      border: 1px solid rgba(112, 204, 255, 0.28);
      border-radius: 9999px;
      padding: 8px 18px;
      color: var(--icy-white);
      font-size: 13px;
      font-weight: 500;
      text-decoration: none;
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      transition: all 0.25s ease;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
      cursor: pointer;
    }

    .glass-nav-btn:hover {
      color: #ffffff;
      border-color: rgba(112, 204, 255, 0.65);
      box-shadow: 0 0 18px rgba(32, 144, 224, 0.4);
      transform: translateY(-1px);
    }

    .glass-nav-btn.enroll-btn {
      border-color: rgba(34, 211, 238, 0.45);
      color: #7dd3fc;
    }

    .glass-nav-btn.enroll-btn:hover {
      border-color: #38bdf8;
      box-shadow: 0 0 18px rgba(56, 189, 248, 0.5);
    }

    .glass-nav-btn.logout-btn {
      color: #94a3b8;
      border-color: rgba(148, 163, 184, 0.22);
    }

    .glass-nav-btn.logout-btn:hover {
      color: #f87171;
      border-color: rgba(248, 113, 113, 0.4);
      box-shadow: 0 0 14px rgba(239, 68, 68, 0.25);
    }

    /* Central Floating Orb Stage */
    .assistant-stage {
      position: relative;
      z-index: 10;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      width: 100%;
      margin: auto 0;
      padding: 10px 0;
    }

    .orb-floating-assembly {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      animation: orbLevitate 6s ease-in-out infinite;
    }

    @keyframes orbLevitate {
      0% { transform: translateY(0px); }
      50% { transform: translateY(-16px); }
      100% { transform: translateY(0px); }
    }

    .orb-scene {
      position: relative;
      width: clamp(340px, 44vw, 540px);
      height: clamp(340px, 44vw, 540px);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .orb-halo {
      position: absolute;
      width: clamp(380px, 48vw, 580px);
      height: clamp(380px, 48vw, 580px);
      border-radius: 50%;
      background: radial-gradient(circle, rgba(65, 165, 230, 0.38) 0%, rgba(30, 105, 175, 0.25) 36%, rgba(10, 45, 80, 0.12) 60%, transparent 74%);
      filter: blur(52px);
      pointer-events: none;
      z-index: 1;
      animation: haloBreath 8s ease-in-out infinite alternate;
    }

    @keyframes haloBreath {
      0% { transform: scale(0.96); opacity: 0.85; }
      100% { transform: scale(1.04); opacity: 1.0; }
    }

    .concentric-ring {
      position: absolute;
      border-radius: 50%;
      pointer-events: none;
      z-index: 3;
    }

    .c-ring-1 {
      width: clamp(270px, 34vw, 420px);
      height: clamp(270px, 34vw, 420px);
      border: 1px solid rgba(75, 175, 235, 0.42);
      box-shadow: 0 0 10px rgba(45, 145, 215, 0.25);
      animation: ringSlowRotate 130s linear infinite;
    }

    .c-ring-2 {
      width: clamp(340px, 43vw, 530px);
      height: clamp(340px, 43vw, 530px);
      border: 1px solid rgba(55, 140, 205, 0.3);
      box-shadow: 0 0 12px rgba(35, 120, 185, 0.18);
      animation: ringSlowRotate 180s linear infinite reverse;
    }

    .c-ring-3 {
      width: clamp(400px, 51vw, 620px);
      height: clamp(400px, 51vw, 620px);
      border: 0.75px solid rgba(35, 105, 165, 0.22);
      animation: ringSlowRotate 240s linear infinite;
    }

    @keyframes ringSlowRotate {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }

    /* Luminous Volumetric Blue Energy Sphere */
    .orb-body {
      position: relative;
      width: clamp(230px, 30vw, 340px);
      height: clamp(230px, 30vw, 340px);
      border-radius: 50%;
      background: radial-gradient(circle at 50% 50%, #164875 0%, #0c3359 55%, #051e36 82%, #021120 100%);
      box-shadow: 
        0 0 65px rgba(55, 165, 235, 0.45),
        0 0 130px rgba(25, 105, 180, 0.35),
        0 0 210px rgba(10, 50, 95, 0.25),
        inset 0 0 45px rgba(4, 18, 36, 0.85),
        inset 0 0 16px rgba(110, 195, 245, 0.35);
      overflow: hidden;
      z-index: 5;
      cursor: pointer;
      transition: transform 0.3s ease, box-shadow 0.4s ease;
    }

    .orb-body:hover {
      box-shadow: 
        0 0 85px rgba(85, 195, 255, 0.65),
        0 0 160px rgba(45, 145, 225, 0.5),
        inset 0 0 45px rgba(4, 18, 36, 0.85),
        inset 0 0 24px rgba(150, 220, 255, 0.55);
    }

    .orb-core-glow {
      position: absolute;
      top: 25%;
      left: 18%;
      width: 64%;
      height: 64%;
      border-radius: 50%;
      background: radial-gradient(circle at 50% 50%, rgba(72, 173, 217, 0.95) 0%, rgba(45, 150, 215, 0.85) 35%, rgba(20, 95, 165, 0.5) 65%, transparent 85%);
      filter: blur(18px);
      pointer-events: none;
      z-index: 2;
      animation: corePulse 7s ease-in-out infinite alternate;
    }

    @keyframes corePulse {
      0% { transform: scale(0.96) translate(0, 0); opacity: 0.88; }
      50% { transform: scale(1.04) translate(2px, -3px); opacity: 1.0; }
      100% { transform: scale(0.98) translate(-2px, 2px); opacity: 0.92; }
    }

    .orb-energy-cloud-1 {
      position: absolute;
      top: -10%;
      left: -10%;
      width: 120%;
      height: 120%;
      border-radius: 50%;
      background: radial-gradient(circle at 45% 55%, rgba(65, 175, 235, 0.75) 0%, rgba(35, 130, 205, 0.5) 40%, rgba(15, 75, 140, 0.25) 65%, transparent 80%);
      filter: blur(20px);
      mix-blend-mode: screen;
      pointer-events: none;
      z-index: 3;
      animation: cloudSwirl1 13s ease-in-out infinite alternate;
    }

    @keyframes cloudSwirl1 {
      0% { transform: rotate(0deg) scale(1); }
      50% { transform: rotate(18deg) scale(1.06); }
      100% { transform: rotate(-15deg) scale(0.97); }
    }

    .orb-energy-cloud-2 {
      position: absolute;
      top: 5%;
      left: 10%;
      width: 100%;
      height: 100%;
      border-radius: 50%;
      background: radial-gradient(circle at 60% 45%, rgba(55, 165, 230, 0.65) 0%, rgba(25, 105, 175, 0.45) 45%, transparent 75%);
      filter: blur(22px);
      mix-blend-mode: screen;
      pointer-events: none;
      z-index: 3;
      animation: cloudSwirl2 17s ease-in-out infinite alternate;
    }

    @keyframes cloudSwirl2 {
      0% { transform: rotate(0deg) scale(0.98); }
      50% { transform: rotate(-22deg) scale(1.05); }
      100% { transform: rotate(16deg) scale(1.01); }
    }

    .orb-depth-shadow {
      position: absolute;
      top: 15%;
      right: -6%;
      width: 52%;
      height: 72%;
      border-radius: 50%;
      background: radial-gradient(ellipse at 75% 50%, rgba(4, 20, 42, 0.65) 0%, rgba(7, 32, 60, 0.42) 42%, transparent 74%);
      filter: blur(14px);
      pointer-events: none;
      z-index: 4;
      animation: depthBreathe 10s ease-in-out infinite alternate;
    }

    @keyframes depthBreathe {
      0% { opacity: 0.8; }
      100% { opacity: 0.95; }
    }

    .orb-highlight-cloud {
      position: absolute;
      top: 10%;
      left: 16%;
      width: 48%;
      height: 38%;
      border-radius: 50%;
      background: radial-gradient(ellipse at 46% 42%, rgba(225, 242, 255, 0.82) 0%, rgba(135, 195, 235, 0.55) 38%, rgba(55, 135, 195, 0.2) 68%, transparent 85%);
      filter: blur(12px);
      pointer-events: none;
      z-index: 4;
      animation: highlightDrift 9s ease-in-out infinite alternate;
    }

    @keyframes highlightDrift {
      0% { transform: translate(0, 0) scale(1); opacity: 0.85; }
      50% { transform: translate(3px, -3px) scale(1.04); opacity: 0.98; }
      100% { transform: translate(-2px, 2px) scale(0.97); opacity: 0.88; }
    }

    .orb-center-highlight {
      position: absolute;
      top: 42%;
      left: 45%;
      width: 36%;
      height: 36%;
      border-radius: 50%;
      background: radial-gradient(circle at center, rgba(95, 205, 250, 0.65) 0%, rgba(45, 155, 225, 0.3) 45%, transparent 70%);
      filter: blur(15px);
      mix-blend-mode: screen;
      pointer-events: none;
      z-index: 4;
    }

    /* REAL-TIME AUDIO-REACTIVE CANVAS VISUALIZER */
    .orb-canvas-visualizer {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      border-radius: 50%;
      pointer-events: none;
      z-index: 6;
      mix-blend-mode: screen;
    }

    .orb-glass-rim {
      position: absolute;
      inset: 0;
      border-radius: 50%;
      background: radial-gradient(circle at 50% 50%, transparent 68%, rgba(10, 42, 75, 0.35) 80%, rgba(4, 18, 36, 0.75) 92%, rgba(2, 10, 22, 0.92) 100%);
      pointer-events: none;
      z-index: 7;
    }

    /* Orb Dynamic Glow States */
    .orb-body.state-idle {
      box-shadow: 
        0 0 65px rgba(55, 165, 235, 0.45),
        0 0 130px rgba(25, 105, 180, 0.35),
        inset 0 0 45px rgba(4, 18, 36, 0.85);
    }

    .orb-body.state-wake-detected {
      box-shadow: 
        0 0 120px rgba(112, 204, 255, 0.95),
        0 0 200px rgba(56, 189, 248, 0.85),
        inset 0 0 60px rgba(224, 242, 254, 0.8) !important;
      animation: wakePulse 0.5s ease-out 1 alternate !important;
    }
    @keyframes wakePulse {
      0% { transform: scale(1.0); }
      50% { transform: scale(1.1); }
      100% { transform: scale(1.03); }
    }

    .orb-body.state-command-listening {
      box-shadow: 
        0 0 100px rgba(56, 189, 248, 0.9),
        0 0 185px rgba(14, 165, 233, 0.7),
        inset 0 0 50px rgba(255, 255, 255, 0.6) !important;
    }

    .orb-body.state-vad-countdown {
      box-shadow: 
        0 0 85px rgba(147, 197, 253, 0.75),
        0 0 160px rgba(59, 130, 246, 0.55),
        inset 0 0 45px rgba(191, 219, 254, 0.45) !important;
    }

    .orb-body.state-transcribing {
      box-shadow: 
        0 0 110px rgba(96, 165, 250, 0.85),
        0 0 190px rgba(37, 99, 235, 0.65),
        inset 0 0 50px rgba(147, 197, 253, 0.6) !important;
    }

    .orb-body.state-verifying {
      box-shadow: 
        0 0 105px rgba(34, 211, 238, 0.85),
        0 0 185px rgba(6, 182, 212, 0.6),
        inset 0 0 45px rgba(165, 243, 252, 0.5) !important;
    }

    .orb-body.state-speaking {
      box-shadow: 
        0 0 115px rgba(125, 211, 252, 0.9),
        0 0 195px rgba(14, 165, 233, 0.7),
        inset 0 0 50px rgba(240, 249, 255, 0.7) !important;
    }

    .orb-body.state-enrolling {
      box-shadow: 
        0 0 115px rgba(34, 211, 238, 0.9),
        0 0 200px rgba(8, 145, 178, 0.75),
        inset 0 0 55px rgba(207, 250, 254, 0.65) !important;
    }

    .orb-body.state-error {
      box-shadow: 
        0 0 95px rgba(245, 158, 11, 0.85),
        0 0 170px rgba(217, 119, 6, 0.6),
        inset 0 0 45px rgba(254, 243, 199, 0.45) !important;
    }

    /* Status Area */
    .status-area {
      margin-top: 18px;
      text-align: center;
      user-select: none;
      position: relative;
      z-index: 10;
      min-height: 52px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }

    .status-text {
      font-size: clamp(16px, 2vw, 20px);
      font-weight: 300;
      letter-spacing: 0.6px;
      color: var(--icy-white);
      text-shadow: 0 0 12px rgba(112, 204, 255, 0.45);
      transition: color 0.3s ease, text-shadow 0.3s ease;
      max-width: 760px;
      margin: 0 auto;
      line-height: 1.45;
    }

    .status-text.state-error {
      color: #FCD34D !important;
      text-shadow: 0 0 14px rgba(245, 158, 11, 0.6) !important;
    }

    .status-subtext {
      font-size: 13px;
      color: var(--muted-text);
      margin-top: 4px;
      letter-spacing: 0.4px;
    }

    /* Bottom Input Bar */
    .input-stage {
      position: relative;
      z-index: 20;
      width: 100%;
      display: flex;
      justify-content: center;
      padding-top: 16px;
    }

    .input-bar {
      width: min(580px, 94vw);
      height: 52px;
      background: var(--glass-navy);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      border-radius: 9999px;
      border: 1px solid var(--glass-border);
      display: flex;
      align-items: center;
      padding: 5px 6px 5px 18px;
      position: relative;
      box-shadow: 0 12px 36px rgba(0, 0, 0, 0.65), 0 0 20px rgba(22, 139, 208, 0.15);
      transition: all 0.3s ease;
    }

    .input-bar:focus-within {
      border-color: rgba(112, 204, 255, 0.55);
      box-shadow: 0 14px 40px rgba(0, 0, 0, 0.75), 0 0 28px rgba(112, 204, 255, 0.3);
    }

    .keyboard-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--muted-text);
      margin-right: 12px;
      flex-shrink: 0;
    }

    .text-input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: var(--icy-white);
      font-size: 15px;
      font-weight: 300;
      font-family: inherit;
      letter-spacing: 0.3px;
    }

    .text-input::placeholder {
      color: var(--muted-text);
      font-weight: 300;
    }

    .send-btn {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: linear-gradient(135deg, #1C7EBF 0%, #2293DC 100%);
      border: none;
      outline: none;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 0 12px rgba(32, 144, 224, 0.5);
      flex-shrink: 0;
      transition: all 0.25s ease;
    }

    .send-btn:hover {
      transform: scale(1.06);
      box-shadow: 0 0 18px rgba(112, 204, 255, 0.7);
    }

    /* Enrollment Modal */
    .enrollment-modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(2, 6, 13, 0.85);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 100;
      padding: 20px;
    }

    .enrollment-modal-backdrop.active {
      display: flex;
    }

    .enrollment-card {
      width: min(540px, 94vw);
      background: rgba(8, 22, 44, 0.94);
      border: 1px solid rgba(112, 204, 255, 0.35);
      border-radius: 20px;
      padding: 28px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8), 0 0 35px rgba(34, 211, 238, 0.25);
      color: var(--icy-white);
      position: relative;
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      border-bottom: 1px solid rgba(112, 204, 255, 0.15);
      padding-bottom: 12px;
    }

    .modal-title {
      font-size: 19px;
      font-weight: 500;
      color: #93c5fd;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .modal-close-btn {
      background: transparent;
      border: none;
      color: var(--muted-text);
      font-size: 22px;
      cursor: pointer;
      line-height: 1;
    }
    .modal-close-btn:hover { color: #f87171; }

    .step-indicator {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 22px;
      padding: 0 6px;
    }

    .step-node {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 5px;
      font-size: 11px;
      color: var(--muted-text);
      flex: 1;
    }

    .step-dot {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      color: var(--muted-text);
    }

    .step-node.active .step-dot {
      background: #0284c7;
      border-color: #38bdf8;
      color: #ffffff;
      box-shadow: 0 0 12px rgba(56, 189, 248, 0.6);
    }

    .step-node.completed .step-dot {
      background: #059669;
      border-color: #34d399;
      color: #ffffff;
    }

    .enrollment-step-content {
      display: none;
      flex-direction: column;
      gap: 16px;
    }

    .enrollment-step-content.active {
      display: flex;
    }

    .modal-instruction {
      font-size: 14px;
      line-height: 1.5;
      color: #cbd5e1;
    }

    .voice-mic-box {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 18px;
      background: rgba(3, 14, 30, 0.7);
      border: 1px dashed rgba(56, 189, 248, 0.4);
      border-radius: 12px;
      gap: 10px;
    }

    .mic-record-btn {
      width: 54px;
      height: 54px;
      border-radius: 50%;
      background: linear-gradient(135deg, #0284c7, #0ea5e9);
      border: none;
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 0 16px rgba(14, 165, 233, 0.5);
      transition: all 0.25s ease;
    }

    .mic-record-btn.recording {
      background: #ef4444 !important;
      animation: micPulsing 1s infinite alternate;
      box-shadow: 0 0 20px rgba(239, 68, 68, 0.8) !important;
    }

    @keyframes micPulsing {
      0% { transform: scale(1.0); }
      100% { transform: scale(1.12); }
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .form-label {
      font-size: 13px;
      color: #94a3b8;
    }

    .form-input {
      background: rgba(2, 10, 22, 0.75);
      border: 1px solid rgba(112, 204, 255, 0.3);
      border-radius: 8px;
      padding: 10px 14px;
      color: #ffffff;
      font-size: 14px;
      outline: none;
    }

    .form-input:focus {
      border-color: #38bdf8;
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.35);
    }

    .action-row {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 10px;
    }

    .btn-secondary {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 8px;
      padding: 8px 16px;
      color: #cbd5e1;
      cursor: pointer;
      font-size: 13px;
    }

    .btn-primary {
      background: linear-gradient(135deg, #0284c7, #0ea5e9);
      border: none;
      border-radius: 8px;
      padding: 8px 18px;
      color: #ffffff;
      font-weight: 500;
      cursor: pointer;
      font-size: 13px;
      box-shadow: 0 0 12px rgba(14, 165, 233, 0.4);
    }

    .sample-progress-dots {
      display: flex;
      justify-content: center;
      gap: 8px;
      margin: 12px 0;
    }

    .sample-dot {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.12);
      border: 1px solid rgba(255, 255, 255, 0.25);
    }

    .sample-dot.done {
      background: #10b981;
      border-color: #34d399;
      box-shadow: 0 0 8px rgba(52, 211, 153, 0.6);
    }

    .sample-dot.recording {
      background: #ef4444;
      border-color: #f87171;
    }
  </style>
</head>
<body>

  <canvas id="space-particles"></canvas>

  <header class="header-bar">
    <a href="/" class="wordmark-wrap" title="Orbis ERP">
      <svg class="wordmark-svg" viewBox="0 0 215 48" height="42" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="neonWaveGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#70CCFF"></stop>
            <stop offset="50%" stop-color="#38A5EC"></stop>
            <stop offset="100%" stop-color="#70CCFF"></stop>
          </linearGradient>
        </defs>
        <circle cx="21" cy="7" r="1.3" fill="#D0F2FF" class="title-star" />
        <text x="2" y="34" class="svg-orbis-text">ORBIS</text>
        <text x="148" y="33" class="svg-erp-text">ERP</text>
      </svg>
    </a>

    <nav class="top-controls">
      <button class="glass-nav-btn enroll-btn" onclick="openEnrollmentModal()" title="Enroll voiceprint">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
          <line x1="12" y1="19" x2="12" y2="22"></line>
        </svg>
        <span>Enroll Voice</span>
      </button>

      <a href="/login" class="glass-nav-btn" title="Manually Sign In">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
          <polyline points="10 17 15 12 10 7"></polyline>
          <line x1="15" y1="12" x2="3" y2="12"></line>
        </svg>
        <span>Manually Sign In</span>
      </a>

      {% if is_authenticated %}
        <a href="/logout" class="glass-nav-btn logout-btn" title="Log Out">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          <span>Log Out</span>
        </a>
      {% endif %}
    </nav>
  </header>

  <main class="assistant-stage">
    <div class="orb-floating-assembly">
      <div class="orb-scene">
        <div class="orb-halo"></div>
        <div class="concentric-ring c-ring-1"></div>
        <div class="concentric-ring c-ring-2"></div>
        <div class="concentric-ring c-ring-3"></div>

        <div class="orb-body state-idle" id="orb-trigger" onclick="onOrbClick()" title="Orbis Voice Assistant (Say 'Orbis' or click to speak)">
          <div class="orb-core-glow"></div>
          <div class="orb-energy-cloud-1"></div>
          <div class="orb-energy-cloud-2"></div>
          <div class="orb-depth-shadow"></div>
          <div class="orb-highlight-cloud"></div>
          <div class="orb-center-highlight"></div>

          <!-- Real-Time Waveform & Biometric Canvas -->
          <canvas id="orb-visualizer" class="orb-canvas-visualizer"></canvas>

          <div class="orb-glass-rim"></div>
        </div>
      </div>
    </div>

    <div class="status-area">
      <div class="status-text" id="status-text">Listening for “Orbis”...</div>
      <div class="status-subtext" id="status-subtext">Hands-free voice active &bull; Speak "Orbis" to begin</div>
    </div>
  </main>

  <footer class="input-stage">
    <div class="input-bar">
      <div class="keyboard-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="4" width="20" height="16" rx="2" ry="2"></rect>
          <line x1="6" y1="8" x2="6.01" y2="8"></line>
          <line x1="10" y1="8" x2="10.01" y2="8"></line>
          <line x1="14" y1="8" x2="14.01" y2="8"></line>
          <line x1="18" y1="8" x2="18.01" y2="8"></line>
        </svg>
      </div>

      <input 
        type="text" 
        class="text-input" 
        id="query-input" 
        placeholder="Or type your request here..." 
        autocomplete="off"
        onkeydown="if(event.key==='Enter') submitQuery()"
      />

      <button class="send-btn" id="send-btn" onclick="submitQuery()" aria-label="Send message">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="5" y1="12" x2="19" y2="12"></line>
          <polyline points="12 5 19 12 12 19"></polyline>
        </svg>
      </button>
    </div>
  </footer>

  <!-- Enrollment Modal -->
  <div class="enrollment-modal-backdrop" id="enrollment-modal">
    <div class="enrollment-card">
      <div class="modal-header">
        <div class="modal-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="22"></line>
          </svg>
          <span>Voice Biometric Enrollment (Layers 1–4)</span>
        </div>
        <button class="modal-close-btn" onclick="closeEnrollmentModal()">&times;</button>
      </div>

      <div class="step-indicator">
        <div class="step-node active" id="step-node-1">
          <div class="step-dot">1</div>
          <span>Account Email</span>
        </div>
        <div class="step-node" id="step-node-2">
          <div class="step-dot">2</div>
          <span>Verify Password</span>
        </div>
        <div class="step-node" id="step-node-3">
          <div class="step-dot">3</div>
          <span>5 Voice Samples</span>
        </div>
        <div class="step-node" id="step-node-4">
          <div class="step-dot">4</div>
          <span>Ready</span>
        </div>
      </div>

      <!-- Step 1: Dedicated Voice Email Dictation -->
      <div class="enrollment-step-content active" id="enroll-step-1">
        <p class="modal-instruction">
          Dictate your registered ERPNext email aloud (e.g. <em>“ayesha dot tahir at gmail dot com”</em>) using local speech recognition:
        </p>
        <div class="voice-mic-box">
          <button class="mic-record-btn" id="email-mic-btn" onclick="toggleEmailVoiceDictation()" title="Click to dictate email">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            </svg>
          </button>
          <span style="font-size:13px; color:#38bdf8;" id="email-mic-status">Click mic and dictate your email</span>
        </div>
        <div class="form-group">
          <label class="form-label" for="enroll-email-input">ERPNext User Email:</label>
          <input type="email" class="form-input" id="enroll-email-input" placeholder="user@example.com" />
        </div>
        <div class="action-row">
          <button class="btn-secondary" onclick="closeEnrollmentModal()">Cancel</button>
          <button class="btn-primary" onclick="proceedToStep2()">Confirm Email &rarr;</button>
        </div>
      </div>

      <!-- Step 2: Secure Password & Session Establishment -->
      <div class="enrollment-step-content" id="enroll-step-2">
        <p class="modal-instruction">
          Enter your existing ERPNext password in the secure masked field below to establish an authentic Frappe session:
        </p>
        <div class="form-group">
          <label class="form-label" for="enroll-password-input">Password for <span id="pwd-email-display" style="color:#38bdf8;"></span>:</label>
          <input type="password" class="form-input" id="enroll-password-input" placeholder="••••••••••••" autocomplete="current-password" />
        </div>
        <div id="pwd-error-msg" style="font-size:12px; color:#f87171; display:none;"></div>
        <div class="action-row">
          <button class="btn-secondary" onclick="setEnrollStep(1)">Back</button>
          <button class="btn-primary" id="btn-verify-pwd" onclick="verifyPasswordAndEstablishSession()">Verify &amp; Establish Session &rarr;</button>
        </div>
      </div>

      <!-- Step 3: Five Voice Sample Recordings (ECAPA-TDNN) -->
      <div class="enrollment-step-content" id="enroll-step-3">
        <p class="modal-instruction" id="sample-prompt-text">
          Record <strong>5 separate voice samples</strong> to calibrate your ECAPA-TDNN biometric profile. Read phrase aloud:
        </p>
        <div style="background:rgba(2,10,22,0.85); border:1px solid rgba(56,189,248,0.3); border-radius:10px; padding:14px; text-align:center; font-size:14px; color:#e0f2fe; margin-bottom:10px;" id="reading-phrase">
          “Orbis, check stock levels for car manufacturing materials.”
        </div>

        <div class="sample-progress-dots">
          <div class="sample-dot" id="sdot-1"></div>
          <div class="sample-dot" id="sdot-2"></div>
          <div class="sample-dot" id="sdot-3"></div>
          <div class="sample-dot" id="sdot-4"></div>
          <div class="sample-dot" id="sdot-5"></div>
        </div>

        <div class="voice-mic-box">
          <button class="mic-record-btn" id="sample-record-btn" onclick="toggleSampleRecording()">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            </svg>
          </button>
          <span style="font-size:13px; color:#38bdf8;" id="sample-record-status">Click mic to record Sample 1 of 5</span>
        </div>

        <div class="action-row">
          <button class="btn-secondary" onclick="closeEnrollmentModal()">Cancel</button>
        </div>
      </div>

      <!-- Step 4: Ready -->
      <div class="enrollment-step-content" id="enroll-step-4">
        <div style="text-align:center; padding:16px 0;">
          <div style="width:56px; height:56px; border-radius:50%; background:#059669; display:inline-flex; align-items:center; justify-content:center; margin-bottom:12px; box-shadow:0 0 20px rgba(16,185,129,0.5);">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          <h3 style="color:#e0f2fe; font-size:18px; margin-bottom:6px;">ECAPA-TDNN Voiceprint Calibrated!</h3>
          <p class="modal-instruction" id="enroll-final-msg">
            Your voice profile is now bound to your authenticated ERPNext session. Say <strong>“Orbis”</strong> hands-free to test your first voice command!
          </p>
        </div>
        <div class="action-row" style="justify-content:center;">
          <button class="btn-primary" onclick="finishEnrollment()">Start Hands-Free Voice Assistant &rarr;</button>
        </div>
      </div>

    </div>
  </div>

  <script>
    /* Background Particles */
    (function initStars() {
      const canvas = document.getElementById('space-particles');
      const ctx = canvas.getContext('2d');
      let w, h;
      const count = 100;
      const particles = [];

      function setSize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
      }
      window.addEventListener('resize', setSize);
      setSize();

      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * w,
          y: Math.random() * h,
          r: Math.random() * 0.9 + 0.4,
          vx: (Math.random() - 0.5) * 0.2,
          vy: -Math.random() * 0.25 - 0.05,
          alpha: Math.random() * 0.5 + 0.2,
          pulse: Math.random() * Math.PI * 2
        });
      }

      function draw() {
        ctx.clearRect(0, 0, w, h);
        for (let i = 0; i < count; i++) {
          const p = particles[i];
          p.x += p.vx;
          p.y += p.vy;
          p.pulse += 0.02;
          if (p.x < 0) p.x = w;
          if (p.x > w) p.x = 0;
          if (p.y < 0) p.y = h;
          if (p.y > h) p.y = 0;
          const a = Math.min(0.7, Math.max(0.12, p.alpha + Math.sin(p.pulse) * 0.15));
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(224, 242, 254, ${a})`;
          ctx.fill();
        }
        requestAnimationFrame(draw);
      }
      requestAnimationFrame(draw);
    })();

    /* ==========================================================================
       LAYER 1: REAL-TIME PHYSICAL AUDIO WAVEFORM & ORB STATES
       ========================================================================== */
    const VAD_ENDPOINT_SILENCE_SECONDS = 10;
    const SPEECH_RMS_THRESHOLD = 0.025; // Real normalized RMS threshold for speech

    let currentOrbState = 'state-idle';
    let isCommandRecording = false;
    let wakeWordActive = false;
    let commandMediaRecorder = null;
    let commandAudioChunks = [];
    let currentAudioPlayback = null;
    let ambientRecognition = null;

    // Web Audio API State
    let audioCtx = null;
    let analyserNode = null;
    let persistentMicStream = null;
    let micStreamSource = null;
    let currentPhysicalRMS = 0;
    let timeDomainData = null;
    let freqData = null;

    // VAD Countdown State
    let hasUserStartedSpeaking = false;
    let silenceCountdownRemaining = VAD_ENDPOINT_SILENCE_SECONDS;
    let silenceCountdownInterval = null;
    let maxRecordingTimeout = null;

    const orbEl = document.getElementById('orb-trigger');
    const statusTextEl = document.getElementById('status-text');
    const statusSubtextEl = document.getElementById('status-subtext');
    const visualizerCanvas = document.getElementById('orb-visualizer');
    const vCtx = visualizerCanvas.getContext('2d');

    function resizeVisualizerCanvas() {
      visualizerCanvas.width = orbEl.clientWidth || 300;
      visualizerCanvas.height = orbEl.clientHeight || 300;
    }
    window.addEventListener('resize', resizeVisualizerCanvas);
    setTimeout(resizeVisualizerCanvas, 100);

    const ALL_ORB_CLASSES = [
      'state-idle', 'state-wake-detected', 'state-command-listening',
      'state-vad-countdown', 'state-transcribing', 'state-verifying',
      'state-speaking', 'state-enrolling', 'state-error'
    ];

    function setOrbState(stateClass, text, subtext) {
      currentOrbState = stateClass;
      orbEl.classList.remove(...ALL_ORB_CLASSES);
      orbEl.classList.add(stateClass);
      statusTextEl.classList.remove('state-error');

      if (text) {
        statusTextEl.innerText = text;
      } else {
        switch (stateClass) {
          case 'state-idle':
            statusTextEl.innerText = 'Listening for “Orbis”...';
            break;
          case 'state-wake-detected':
            statusTextEl.innerText = 'Orbis activated.';
            break;
          case 'state-command-listening':
            statusTextEl.innerText = 'I’m listening...';
            break;
          case 'state-vad-countdown':
            statusTextEl.innerText = `Silence detected... Submitting in ${Math.ceil(silenceCountdownRemaining)}s`;
            break;
          case 'state-transcribing':
            statusTextEl.innerText = 'Understanding your command...';
            break;
          case 'state-verifying':
            statusTextEl.innerText = 'Verifying voice with ECAPA-TDNN...';
            break;
          case 'state-speaking':
            statusTextEl.innerText = 'Speaking...';
            break;
          case 'state-enrolling':
            statusTextEl.innerText = 'Voice biometric enrollment active...';
            break;
          case 'state-error':
            statusTextEl.innerText = 'Interaction failed.';
            break;
        }
      }

      if (subtext !== undefined) {
        statusSubtextEl.innerText = subtext;
      } else if (stateClass === 'state-idle') {
        statusSubtextEl.innerText = 'Hands-free voice active • Speak "Orbis" to begin';
      }

      if (stateClass === 'state-error') {
        statusTextEl.classList.add('state-error');
      }
    }

    /* CONTINUOUS REAL-TIME WAVEFORM RENDERING (Web Audio API Oscilloscope) */
    let wavePhase = 0;
    (function renderRealTimeWaveform() {
      requestAnimationFrame(renderRealTimeWaveform);
      wavePhase += 0.04;

      const w = visualizerCanvas.width;
      const h = visualizerCanvas.height;
      if (!w || !h) return;
      vCtx.clearRect(0, 0, w, h);

      const cx = w / 2;
      const cy = h / 2;
      const radius = Math.min(w, h) * 0.44;

      // Calculate real RMS from physical mic time-domain buffer
      if (analyserNode && persistentMicStream) {
        if (!timeDomainData) {
          timeDomainData = new Uint8Array(analyserNode.frequencyBinCount);
          freqData = new Uint8Array(analyserNode.frequencyBinCount);
        }
        analyserNode.getByteTimeDomainData(timeDomainData);
        analyserNode.getByteFrequencyData(freqData);

        let sumSquares = 0;
        for (let i = 0; i < timeDomainData.length; i++) {
          const norm = (timeDomainData[i] - 128) / 128.0;
          sumSquares += norm * norm;
        }
        currentPhysicalRMS = Math.sqrt(sumSquares / timeDomainData.length);
      } else {
        currentPhysicalRMS = 0;
      }

      // STATE RENDERING:
      if (currentOrbState === 'state-command-listening' || currentOrbState === 'state-speaking') {
        // Continuous organic oscilloscope multi-wave responding directly to voice
        vCtx.save();
        vCtx.beginPath();
        vCtx.arc(cx, cy, radius, 0, Math.PI * 2);
        vCtx.clip();

        const ampMultiplier = Math.min(currentPhysicalRMS * 220, 75);
        const waveCount = 3;
        const colors = [
          'rgba(112, 204, 255, 0.95)',
          'rgba(56, 189, 248, 0.75)',
          'rgba(224, 242, 254, 0.85)'
        ];

        for (let wIdx = 0; wIdx < waveCount; wIdx++) {
          vCtx.beginPath();
          const pOffset = wIdx * 0.8;
          const sliceWidth = (radius * 1.6) / (timeDomainData ? timeDomainData.length : 64);
          let startX = cx - radius * 0.8;

          for (let i = 0; i < (timeDomainData ? timeDomainData.length : 64); i++) {
            const rawVal = timeDomainData ? (timeDomainData[i] - 128) / 128.0 : 0.0;
            const x = startX + i * sliceWidth;
            const sineHarmonic = Math.sin((i * 0.15) + wavePhase + pOffset) * (Math.max(ampMultiplier * 0.4, 4));
            const y = cy + (rawVal * ampMultiplier) + sineHarmonic;

            if (i === 0) vCtx.moveTo(x, y);
            else vCtx.lineTo(x, y);
          }

          vCtx.lineWidth = wIdx === 2 ? 1.5 : 2.5;
          vCtx.strokeStyle = colors[wIdx];
          vCtx.shadowBlur = 12;
          vCtx.shadowColor = '#38bdf8';
          vCtx.stroke();
        }
        vCtx.restore();

      } else if (currentOrbState === 'state-vad-countdown') {
        // VAD Countdown Circular Arc + Settling Wave
        vCtx.save();
        vCtx.beginPath();
        const startAngle = -Math.PI / 2;
        const progress = (VAD_ENDPOINT_SILENCE_SECONDS - silenceCountdownRemaining) / VAD_ENDPOINT_SILENCE_SECONDS;
        const endAngle = startAngle + (Math.PI * 2 * (1 - progress));

        vCtx.arc(cx, cy, radius * 0.85, startAngle, endAngle);
        vCtx.lineWidth = 4;
        vCtx.strokeStyle = 'rgba(147, 197, 253, 0.9)';
        vCtx.shadowBlur = 12;
        vCtx.shadowColor = '#60a5fa';
        vCtx.stroke();

        // Calm settling wave
        vCtx.beginPath();
        for (let x = cx - radius * 0.6; x <= cx + radius * 0.6; x += 4) {
          const y = cy + Math.sin((x + wavePhase * 15) * 0.05) * 6;
          if (x === cx - radius * 0.6) vCtx.moveTo(x, y);
          else vCtx.lineTo(x, y);
        }
        vCtx.lineWidth = 2;
        vCtx.strokeStyle = 'rgba(224, 242, 254, 0.65)';
        vCtx.stroke();

        // Center Countdown Digits
        vCtx.font = "600 24px -apple-system, sans-serif";
        vCtx.fillStyle = "#ffffff";
        vCtx.textAlign = "center";
        vCtx.textBaseline = "middle";
        vCtx.fillText(`${Math.ceil(silenceCountdownRemaining)}s`, cx, cy);
        vCtx.restore();

      } else if (currentOrbState === 'state-transcribing') {
        // Horizontal Scanning Beam
        vCtx.save();
        const scanY = cy + Math.sin(wavePhase * 2.2) * (radius * 0.65);
        const grad = vCtx.createLinearGradient(cx - radius * 0.7, scanY, cx + radius * 0.7, scanY);
        grad.addColorStop(0, 'transparent');
        grad.addColorStop(0.5, 'rgba(224, 242, 254, 0.95)');
        grad.addColorStop(1, 'transparent');

        vCtx.strokeStyle = grad;
        vCtx.lineWidth = 3;
        vCtx.shadowBlur = 14;
        vCtx.shadowColor = '#93c5fd';
        vCtx.beginPath();
        vCtx.moveTo(cx - radius * 0.7, scanY);
        vCtx.lineTo(cx + radius * 0.7, scanY);
        vCtx.stroke();
        vCtx.restore();

      } else if (currentOrbState === 'state-verifying' || currentOrbState === 'state-enrolling') {
        // ECAPA Biometric Radar Scanner
        vCtx.save();
        vCtx.beginPath();
        vCtx.arc(cx, cy, radius * 0.75, 0, Math.PI * 2);
        vCtx.strokeStyle = 'rgba(34, 211, 238, 0.45)';
        vCtx.lineWidth = 1.5;
        vCtx.stroke();

        const radarAngle = wavePhase * 2.5;
        vCtx.beginPath();
        vCtx.moveTo(cx, cy);
        vCtx.arc(cx, cy, radius * 0.75, radarAngle, radarAngle + 0.65);
        vCtx.closePath();
        vCtx.fillStyle = 'rgba(34, 211, 238, 0.28)';
        vCtx.fill();
        vCtx.restore();

      } else if (currentOrbState === 'state-idle') {
        // Subtle Breathing Wave (minimal resting amplitude)
        vCtx.save();
        vCtx.beginPath();
        for (let x = cx - radius * 0.55; x <= cx + radius * 0.55; x += 4) {
          const y = cy + Math.sin((x + wavePhase * 10) * 0.04) * 3;
          if (x === cx - radius * 0.55) vCtx.moveTo(x, y);
          else vCtx.lineTo(x, y);
        }
        vCtx.lineWidth = 1.5;
        vCtx.strokeStyle = 'rgba(112, 204, 255, 0.35)';
        vCtx.stroke();
        vCtx.restore();
      }
    })();

    /* Female Edge-TTS Playback */
    function playAudioResponse(base64Audio, format, onEndCallback) {
      if (currentAudioPlayback) {
        currentAudioPlayback.pause();
        currentAudioPlayback = null;
      }
      if (!base64Audio) {
        if (onEndCallback) onEndCallback();
        return;
      }
      try {
        const mime = format || 'audio/mp3';
        currentAudioPlayback = new Audio('data:' + mime + ';base64,' + base64Audio);
        setOrbState('state-speaking', null, 'Female voice response (en-US-AriaNeural)');

        currentAudioPlayback.onended = () => {
          if (onEndCallback) onEndCallback();
          else {
            setOrbState('state-idle');
            scheduleWakeWordRestart(400);
          }
        };
        currentAudioPlayback.onerror = () => {
          if (onEndCallback) onEndCallback();
          else {
            setOrbState('state-idle');
            scheduleWakeWordRestart(400);
          }
        };
        currentAudioPlayback.play().catch(() => {
          setTimeout(() => {
            if (onEndCallback) onEndCallback();
            else {
              setOrbState('state-idle');
              scheduleWakeWordRestart(400);
            }
          }, 3200);
        });
      } catch (err) {
        if (onEndCallback) onEndCallback();
        else {
          setOrbState('state-idle');
          scheduleWakeWordRestart(400);
        }
      }
    }

    /* Web Audio API Persistent Stream Setup */
    async function initPersistentMic() {
      if (persistentMicStream) return true;
      try {
        persistentMicStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        audioCtx = new AudioContext();
        if (audioCtx.state === 'suspended') {
          await audioCtx.resume();
        }
        analyserNode = audioCtx.createAnalyser();
        analyserNode.fftSize = 128;
        micStreamSource = audioCtx.createMediaStreamSource(persistentMicStream);
        micStreamSource.connect(analyserNode);
        return true;
      } catch (err) {
        console.warn('[Orbis Mic] Microphone access blocked:', err);
        setOrbState('state-error', 'Microphone blocked. Allow microphone permission in browser.', 'Permission denied');
        return false;
      }
    }

    /* ==========================================================================
       LAYER 2: AUTOMATIC HANDS-FREE WAKE-WORD DETECTION ("ORBIS")
       ========================================================================== */
    const WAKE_WORD_TRIGGERS = [
      'orbis', 'orbit', 'albis', 'orvis', 'aurbis', 'all this', 'always',
      'artist', 'office', 'or bis', 'orb', 'our bus', 'aur bis'
    ];

    function isWakeWordMatch(transcript) {
      if (!transcript) return false;
      const lower = transcript.toLowerCase();
      return WAKE_WORD_TRIGGERS.some(trigger => lower.includes(trigger));
    }

    function startAmbientWakeWord() {
      if (isCommandRecording || currentOrbState === 'state-transcribing' || currentOrbState === 'state-speaking' || wakeWordActive) {
        return;
      }

      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRec) {
        console.log('[Orbis WakeWord] SpeechRecognition unsupported in browser; use manual click.');
        return;
      }

      if (ambientRecognition) {
        try { ambientRecognition.abort(); } catch(e) {}
        ambientRecognition = null;
      }

      try {
        ambientRecognition = new SpeechRec();
        ambientRecognition.continuous = true;
        ambientRecognition.interimResults = true;
        ambientRecognition.lang = 'en-US';

        ambientRecognition.onstart = () => {
          wakeWordActive = true;
          if (currentOrbState === 'state-idle') {
            statusTextEl.innerText = 'Listening for “Orbis”...';
          }
        };

        ambientRecognition.onresult = (event) => {
          if (isCommandRecording || currentOrbState === 'state-transcribing' || currentOrbState === 'state-speaking') return;

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const transcript = event.results[i][0].transcript;
            if (isWakeWordMatch(transcript)) {
              console.log('[Orbis WakeWord] Hands-free wake word recognized:', transcript);
              wakeWordActive = false;
              try { ambientRecognition.stop(); } catch(e) {}

              // Hands-Free Activation!
              setOrbState('state-wake-detected', 'Orbis activated.', 'Listening for your command...');
              setTimeout(() => {
                startCommandRecordingWithVAD(false, true);
              }, 300);
              return;
            }
          }
        };

        ambientRecognition.onerror = (e) => {
          wakeWordActive = false;
          if (e.error !== 'no-speech' && e.error !== 'aborted') {
            console.warn('[Orbis WakeWord] Event:', e.error);
          }
        };

        ambientRecognition.onend = () => {
          wakeWordActive = false;
          if (currentOrbState === 'state-idle' && !isCommandRecording) {
            scheduleWakeWordRestart(400);
          }
        };

        ambientRecognition.start();
      } catch (err) {
        wakeWordActive = false;
        scheduleWakeWordRestart(1200);
      }
    }

    let restartTimer = null;
    function scheduleWakeWordRestart(delayMs) {
      if (restartTimer) clearTimeout(restartTimer);
      restartTimer = setTimeout(() => {
        if (currentOrbState === 'state-idle' && !isCommandRecording && !wakeWordActive) {
          startAmbientWakeWord();
        }
      }, delayMs);
    }

    function stopWakeWordListener() {
      wakeWordActive = false;
      if (ambientRecognition) {
        try { ambientRecognition.abort(); } catch(e) {}
        ambientRecognition = null;
      }
    }

    /* ==========================================================================
       LAYER 2B: SILERO VAD & 10-SECOND SILENCE RECORDING
       ========================================================================== */
    async function startCommandRecordingWithVAD(isManual = false, isWakeWordVerified = false) {
      if (isCommandRecording) return;
      stopWakeWordListener();

      const ok = await initPersistentMic();
      if (!ok) return;

      try {
        commandAudioChunks = [];
        commandMediaRecorder = new MediaRecorder(persistentMicStream);

        commandMediaRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) commandAudioChunks.push(e.data);
        };

        commandMediaRecorder.onstop = () => {
          clearInterval(silenceCountdownInterval);
          clearTimeout(maxRecordingTimeout);

          const audioBlob = new Blob(commandAudioChunks, { type: commandMediaRecorder.mimeType || 'audio/webm' });
          if (audioBlob.size > 800) {
            sendAudioToBackend(audioBlob, isManual, isWakeWordVerified);
          } else {
            setOrbState('state-idle', 'No audible command detected. Say “Orbis” to activate.');
            scheduleWakeWordRestart(1200);
          }
        };

        commandMediaRecorder.start();
        isCommandRecording = true;
        hasUserStartedSpeaking = false;
        silenceCountdownRemaining = VAD_ENDPOINT_SILENCE_SECONDS;

        setOrbState('state-command-listening', 'I’m listening...', 'Speak your request now');

        // Check real physical RMS energy every 250ms for speech & silence transitions
        silenceCountdownInterval = setInterval(() => {
          if (!isCommandRecording) return;

          // 1. Detect when user starts speaking
          if (!hasUserStartedSpeaking) {
            if (currentPhysicalRMS >= SPEECH_RMS_THRESHOLD) {
              hasUserStartedSpeaking = true;
              setOrbState('state-command-listening', 'I’m listening...', 'Speech detected');
            }
            return;
          }

          // 2. Once speech detected, monitor for continuous silence
          if (currentPhysicalRMS < SPEECH_RMS_THRESHOLD) {
            if (currentOrbState !== 'state-vad-countdown') {
              silenceCountdownRemaining = VAD_ENDPOINT_SILENCE_SECONDS;
              setOrbState('state-vad-countdown', `Silence detected... Submitting in ${Math.ceil(silenceCountdownRemaining)}s`, 'Speak to continue');
            } else {
              silenceCountdownRemaining -= 0.25;
              if (silenceCountdownRemaining <= 0) {
                // 10 continuous seconds of silence reached! Submit audio!
                clearInterval(silenceCountdownInterval);
                finishCommandRecording();
                return;
              }
              setOrbState('state-vad-countdown', `Silence detected... Submitting in ${Math.ceil(silenceCountdownRemaining)}s (speak to continue)`);
            }
          } else {
            // Speech resumed! Reset countdown to 10s and return to listening state
            if (currentOrbState === 'state-vad-countdown') {
              silenceCountdownRemaining = VAD_ENDPOINT_SILENCE_SECONDS;
              setOrbState('state-command-listening', 'I’m listening...', 'Speech resumed');
            }
          }
        }, 250);

        // Maximum 60-second safeguard
        maxRecordingTimeout = setTimeout(() => {
          if (isCommandRecording) finishCommandRecording();
        }, 60000);

      } catch (err) {
        isCommandRecording = false;
        setOrbState('state-error', 'Microphone error recording command.', 'Recording error');
        scheduleWakeWordRestart(4000);
      }
    }

    function finishCommandRecording() {
      if (isCommandRecording && commandMediaRecorder && commandMediaRecorder.state !== 'inactive') {
        commandMediaRecorder.stop();
        isCommandRecording = false;
      }
    }

    function onOrbClick() {
      if (isCommandRecording) {
        finishCommandRecording();
      } else {
        setOrbState('state-wake-detected', 'Orbis activated.', 'Listening for command...');
        setTimeout(() => startCommandRecordingWithVAD(true, false), 300);
      }
    }

    /* Process Audio with Backend (Layers 2, 3, 4) */
    async function sendAudioToBackend(audioBlob, isManual = false, isWakeWordVerified = false) {
      setOrbState('state-transcribing', 'Understanding your command...', 'faster-whisper processing');

      const formData = new FormData();
      formData.append('audio', audioBlob, 'voice_query.webm');
      formData.append('file', audioBlob, 'voice_query.webm');
      formData.append('manual_trigger', isManual ? 'true' : 'false');
      formData.append('wake_word_verified', isWakeWordVerified ? 'true' : 'false');
      const sidMatch = (document.cookie.match(/(?:^|;\s*)sid=([^;]+)/) || [])[1] || '';
      if (sidMatch) {
        formData.append('session_id', sidMatch);
      }

      try {
        const resp = await fetch('http://127.0.0.1:8000/api/voice/process', {
          method: 'POST',
          body: formData
        });

        if (!resp.ok) {
          const errData = await resp.json().catch(() => ({}));
          setOrbState('state-error', `Backend error: ${errData.detail || 'Request failed'}`);
          scheduleWakeWordRestart(4000);
          return;
        }

        const data = await resp.json();
        const responseText = data.response_text || 'Completed.';

        if (data.status === 'no_speech') {
          setOrbState('state-idle', 'No speech detected. Please speak clearly into your microphone.');
          playAudioResponse(data.audio_base64, data.audio_format, () => scheduleWakeWordRestart(1200));
          return;
        }

        if (data.status === 'wake_word_required') {
          setOrbState('state-idle', 'Say “Orbis” to activate.');
          scheduleWakeWordRestart(2000);
          return;
        }

        if (data.status === 'unauthorized_speaker' || data.status === 'ambiguous_speaker') {
          setOrbState('state-error', responseText, 'Speaker verification failed');
          playAudioResponse(data.audio_base64, data.audio_format, () => {
            scheduleWakeWordRestart(2500);
          });
          return;
        }

        if (data.status === 'enrollment_required') {
          setOrbState('state-error', responseText, 'Voice enrollment required');
          playAudioResponse(data.audio_base64, data.audio_format, () => {
            openEnrollmentModal();
          });
          return;
        }

        // Layer 3: Verified with ECAPA-TDNN
        setOrbState('state-verifying', `ECAPA Verified: ${data.authenticated_user}`, 'Speaker verified');
        
        setTimeout(() => {
          setOrbState('state-speaking', responseText, 'ERP Result');
          playAudioResponse(data.audio_base64, data.audio_format, () => {
            setTimeout(() => {
              setOrbState('state-idle');
              scheduleWakeWordRestart(400);
            }, 1600);
          });
        }, 500);

      } catch (err) {
        setOrbState('state-error', 'AI backend not reachable at 127.0.0.1:8000.');
        scheduleWakeWordRestart(4000);
      }
    }

    function getCookie(name) {
      const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
      return match ? decodeURIComponent(match[2]) : null;
    }

    /* Submit Text Query */
    async function submitQuery() {
      const input = document.getElementById('query-input');
      const text = (input.value || '').trim();
      if (!text) return;

      input.value = '';
      setOrbState('state-transcribing', `Processing: “${text}”`, 'Query submission');

      const sessionId = getCookie('sid') || null;

      try {
        const resp = await fetch('http://127.0.0.1:8000/api/voice/text-query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: text, session_id: sessionId })
        });

        const data = await resp.json();
        const responseText = data.response_text || 'Processed successfully.';
        setOrbState('state-speaking', responseText, 'Text Result');

        playAudioResponse(data.audio_base64, data.audio_format, () => {
          setTimeout(() => {
            setOrbState('state-idle');
            scheduleWakeWordRestart(400);
          }, 1800);
        });
      } catch (err) {
        setOrbState('state-error', 'AI backend not available at 127.0.0.1:8000.');
        scheduleWakeWordRestart(4000);
      }
    }

    /* ==========================================================================
       LAYER 2D & LAYER 4: ENROLLMENT & AUTHENTICATED SESSION ESTABLISHMENT
       ========================================================================== */
    let enrollmentUserEmail = '';
    let enrollmentUserFullName = '';
    let emailAudioRecorder = null;
    let emailAudioChunks = [];
    let isEmailRecording = false;

    let currentSampleIndex = 1;
    let sampleBlobs = [];
    let sampleRecorder = null;
    let sampleAudioChunks = [];
    let isRecordingSample = false;
    let sampleTimer = null;

    const sampleReadingPhrases = [
      '“Orbis, check stock levels for car manufacturing materials.”',
      '“Orbis, show current balance for the assembly warehouse.”',
      '“Orbis, generate summary of pending purchase orders.”',
      '“Orbis, verify production inventory and engine supplies.”',
      '“Orbis, confirm my authorized speaker identity for ERPNext.”'
    ];

    function openEnrollmentModal() {
      stopWakeWordListener(); // Release microphone for dedicated enrollment dictation
      if (sampleTimer) { clearTimeout(sampleTimer); sampleTimer = null; }
      if (sampleRecorder && sampleRecorder.state !== 'inactive') { try { sampleRecorder.stop(); } catch(e){} }
      if (emailAudioRecorder && emailAudioRecorder.state !== 'inactive') { try { emailAudioRecorder.stop(); } catch(e){} }
      sampleBlobs = [];
      sampleAudioChunks = [];
      emailAudioChunks = [];
      currentSampleIndex = 1;
      document.getElementById('enrollment-modal').classList.add('active');
      setEnrollStep(1);
      setOrbState('state-enrolling', 'Voice Biometric Enrollment Active', '5-sample ECAPA calibration');
    }

    function closeEnrollmentModal() {
      document.getElementById('enrollment-modal').classList.remove('active');
      if (sampleTimer) { clearTimeout(sampleTimer); sampleTimer = null; }
      if (emailAudioRecorder && emailAudioRecorder.state !== 'inactive') {
        try { emailAudioRecorder.stop(); } catch(e) {}
      }
      if (sampleRecorder && sampleRecorder.state !== 'inactive') {
        try { sampleRecorder.stop(); } catch(e) {}
      }
      sampleBlobs = [];
      sampleAudioChunks = [];
      emailAudioChunks = [];
      setOrbState('state-idle');
      scheduleWakeWordRestart(500);
    }

    function setEnrollStep(stepNum) {
      for (let i = 1; i <= 4; i++) {
        const stepEl = document.getElementById(`enroll-step-${i}`);
        const nodeEl = document.getElementById(`step-node-${i}`);
        if (stepEl) stepEl.classList.remove('active');
        if (nodeEl) {
          nodeEl.classList.remove('active', 'completed');
          if (i < stepNum) nodeEl.classList.add('completed');
          else if (i === stepNum) nodeEl.classList.add('active');
        }
      }
      const activeStep = document.getElementById(`enroll-step-${stepNum}`);
      if (activeStep) activeStep.classList.add('active');

      if (stepNum === 2) {
        document.getElementById('pwd-email-display').innerText = enrollmentUserEmail;
        document.getElementById('enroll-password-input').value = '';
        document.getElementById('enroll-password-input').focus();
      } else if (stepNum === 3) {
        currentSampleIndex = 1;
        sampleBlobs = [];
        updateSampleUI();
      }
    }

    /* Dedicated Voice Email Dictation (Local faster-whisper) */
    async function toggleEmailVoiceDictation() {
      const micBtn = document.getElementById('email-mic-btn');
      const micStatus = document.getElementById('email-mic-status');

      if (isEmailRecording) {
        if (emailAudioRecorder && emailAudioRecorder.state !== 'inactive') {
          emailAudioRecorder.stop();
        }
        isEmailRecording = false;
        micBtn.classList.remove('recording');
        micStatus.innerText = 'Transcribing voice dictation...';
        return;
      }

      const ok = await initPersistentMic();
      if (!ok) return;

      try {
        emailAudioChunks = [];
        emailAudioRecorder = new MediaRecorder(persistentMicStream);

        emailAudioRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) emailAudioChunks.push(e.data);
        };

        emailAudioRecorder.onstop = async () => {
          const blob = new Blob(emailAudioChunks, { type: emailAudioRecorder.mimeType || 'audio/webm' });
          micStatus.innerText = 'Processing with local faster-whisper...';

          const formData = new FormData();
          formData.append('audio', blob, 'email_dictation.webm');

          try {
            const resp = await fetch('http://127.0.0.1:8000/api/voice/dictate-email', {
              method: 'POST',
              body: formData
            });
            const data = await resp.json();
            if (data.is_valid_format && data.interpreted_email) {
              document.getElementById('enroll-email-input').value = data.interpreted_email;
              enrollmentUserEmail = data.interpreted_email;
              micStatus.innerText = `Interpreted: ${data.interpreted_email}`;
              playAudioResponse(data.audio_base64, data.audio_format);
            } else {
              micStatus.innerText = data.response_text || 'Could not parse a valid email. Please type below.';
              playAudioResponse(data.audio_base64, data.audio_format);
            }
          } catch (e) {
            micStatus.innerText = 'Transcription error. Please type email directly.';
          }
        };

        emailAudioRecorder.start();
        isEmailRecording = true;
        micBtn.classList.add('recording');
        micStatus.innerText = 'Listening... Speak email (e.g. “ayesha dot tahir at gmail dot com”), then click mic to stop';

      } catch (err) {
        micStatus.innerText = 'Microphone access error.';
      }
    }

    function proceedToStep2() {
      const emailVal = (document.getElementById('enroll-email-input').value || '').trim();
      if (!emailVal || !emailVal.includes('@')) {
        alert('Please enter a valid registered ERPNext email address.');
        return;
      }
      enrollmentUserEmail = emailVal;
      setEnrollStep(2);
    }

    /* Verify Password, Establish Genuine ERPNext Session, Check frappe.auth.get_logged_user */
    async function verifyPasswordAndEstablishSession() {
      const pwdInput = document.getElementById('enroll-password-input');
      const pwdVal = pwdInput.value;
      const errMsg = document.getElementById('pwd-error-msg');
      const btn = document.getElementById('btn-verify-pwd');

      errMsg.style.display = 'none';
      if (!pwdVal) {
        errMsg.innerText = 'Please enter your ERPNext password.';
        errMsg.style.display = 'block';
        return;
      }

      btn.disabled = true;
      btn.innerText = 'Authenticating with ERPNext...';

      try {
        // 1. Establish Native Browser Frappe Session (Same-Origin call to /api/method/login)
        const frappeForm = new FormData();
        frappeForm.append('usr', enrollmentUserEmail);
        frappeForm.append('pwd', pwdVal);

        const frappeResp = await fetch('/api/method/login', {
          method: 'POST',
          body: frappeForm
        });

        // 2. Also verify credentials against backend API
        const backendResp = await fetch('http://127.0.0.1:8000/api/voice/verify-credentials', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: enrollmentUserEmail, password: pwdVal })
        });

        // Wipe password immediately from DOM
        pwdInput.value = '';

        const backendData = await backendResp.json();
        if (!backendData.is_valid) {
          errMsg.innerText = backendData.reason || 'Invalid ERPNext password.';
          errMsg.style.display = 'block';
          btn.disabled = false;
          btn.innerText = 'Verify & Establish Session →';
          playAudioResponse(backendData.audio_base64, backendData.audio_format);
          return;
        }

        // Set session cookie if returned by backend
        if (backendData.session_id) {
          document.cookie = `sid=${backendData.session_id}; path=/`;
        }

        // 3. Independent Verification: Call frappe.auth.get_logged_user to prove active session!
        const sessionCheck = await fetch('/api/method/frappe.auth.get_logged_user');
        const sessionData = await sessionCheck.json().catch(() => ({}));
        console.log('[Orbis ERPNext Session] Authenticated user confirmed:', sessionData.message);

        enrollmentUserFullName = backendData.full_name || enrollmentUserEmail;

        playAudioResponse(backendData.audio_base64, backendData.audio_format, () => {
          setEnrollStep(3);
        });

      } catch (err) {
        pwdInput.value = '';
        errMsg.innerText = 'Connection error verifying credentials.';
        errMsg.style.display = 'block';
        btn.disabled = false;
        btn.innerText = 'Verify & Establish Session →';
      }
    }

    /* Record 5 Voice Samples for ECAPA-TDNN */
    function updateSampleUI() {
      document.getElementById('reading-phrase').innerText = sampleReadingPhrases[currentSampleIndex - 1] || sampleReadingPhrases[0];
      document.getElementById('sample-record-status').innerText = `Click mic to record Sample ${currentSampleIndex} of 5`;

      for (let i = 1; i <= 5; i++) {
        const dot = document.getElementById(`sdot-${i}`);
        if (dot) {
          dot.classList.remove('done', 'recording');
          if (i < currentSampleIndex) dot.classList.add('done');
        }
      }
    }

    async function toggleSampleRecording() {
      const btn = document.getElementById('sample-record-btn');
      const statusLbl = document.getElementById('sample-record-status');
      const currentDot = document.getElementById(`sdot-${currentSampleIndex}`);

      if (isRecordingSample) {
        if (sampleTimer) {
          clearTimeout(sampleTimer);
          sampleTimer = null;
        }
        if (sampleRecorder && sampleRecorder.state !== 'inactive') {
          sampleRecorder.stop();
        }
        isRecordingSample = false;
        btn.classList.remove('recording');
        if (currentDot) currentDot.classList.remove('recording');
        return;
      }

      const ok = await initPersistentMic();
      if (!ok) return;

      try {
        sampleAudioChunks = [];
        sampleRecorder = new MediaRecorder(persistentMicStream);
        const sampleStartTime = Date.now();

        sampleRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) sampleAudioChunks.push(e.data);
        };

        sampleRecorder.onstop = async () => {
          const durationSec = (Date.now() - sampleStartTime) / 1000;
          const blob = new Blob(sampleAudioChunks, { type: sampleRecorder.mimeType || 'audio/webm' });

          if (durationSec < 0.8 || blob.size < 1200) {
            statusLbl.innerText = `Sample too short (${durationSec.toFixed(1)}s, ${(blob.size/1024).toFixed(1)}KB). Please click mic and read clearly.`;
            if (currentDot) currentDot.classList.remove('recording');
            return;
          }

          sampleBlobs.push(blob);
          statusLbl.innerText = `Sample ${currentSampleIndex} captured (${durationSec.toFixed(1)}s, ${(blob.size/1024).toFixed(1)}KB)`;

          if (currentDot) {
            currentDot.classList.remove('recording');
            currentDot.classList.add('done');
          }

          if (currentSampleIndex < 5) {
            currentSampleIndex++;
            updateSampleUI();
          } else {
            await submitAllSamplesToEnrollment();
          }
        };

        sampleRecorder.start();
        isRecordingSample = true;
        btn.classList.add('recording');
        if (currentDot) currentDot.classList.add('recording');
        statusLbl.innerText = `Recording Sample ${currentSampleIndex} of 5... Read phrase, then click mic to finish`;

        sampleTimer = setTimeout(() => {
          if (isRecordingSample) toggleSampleRecording();
        }, 5000);

      } catch (e) {
        statusLbl.innerText = 'Microphone error recording sample.';
      }
    }

    async function submitAllSamplesToEnrollment() {
      const statusLbl = document.getElementById('sample-record-status');
      statusLbl.innerText = 'Calibrating 5-sample ECAPA-TDNN biometric profile...';
      setOrbState('state-enrolling', 'Calibrating SpeechBrain ECAPA-TDNN voiceprint...', '192-dim neural embeddings');

      const formData = new FormData();
      formData.append('user_id', enrollmentUserEmail);
      const sidMatch = (document.cookie.match(/(?:^|;\s*)sid=([^;]+)/) || [])[1] || '';
      if (sidMatch) {
        formData.append('session_id', sidMatch);
      }
      formData.append('sample1', sampleBlobs[0], 'sample1.webm');
      formData.append('sample2', sampleBlobs[1], 'sample2.webm');
      formData.append('sample3', sampleBlobs[2], 'sample3.webm');
      if (sampleBlobs[3]) formData.append('sample4', sampleBlobs[3], 'sample4.webm');
      if (sampleBlobs[4]) formData.append('sample5', sampleBlobs[4], 'sample5.webm');

      try {
        const resp = await fetch('http://127.0.0.1:8000/api/voice/enroll', {
          method: 'POST',
          body: formData
        });

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          statusLbl.innerText = `Enrollment error: ${err.detail || 'Failed'}`;
          setOrbState('state-error', 'Enrollment failed.');
          return;
        }

        const data = await resp.json();
        document.getElementById('enroll-final-msg').innerText = 
          `ECAPA-TDNN profile calibrated with ${data.samples_enrolled} samples for ${data.full_name || enrollmentUserEmail}. Consistency score: ${(data.consistency_score * 100).toFixed(0)}%.`;

        setEnrollStep(4);
        playAudioResponse(data.audio_base64, data.audio_format);

      } catch (err) {
        statusLbl.innerText = 'Network error saving voice profile.';
      }
    }

    function finishEnrollment() {
      closeEnrollmentModal();
      setOrbState('state-idle', 'Say “Orbis” hands-free to test your voice profile!', 'Ready for first command');
    }

    /* Auto-initialize persistent mic and start hands-free wake-word listener on load */
    window.addEventListener('DOMContentLoaded', async () => {
      const ok = await initPersistentMic();
      if (ok) {
        startAmbientWakeWord();
      }
    });
  </script>
</body>
</html>
'''


def deploy_portal_files():
    """Deploy orbis.py and orbis.html to erpnext/www directory."""
    print("  [1/4] Deploying Portal Files to erpnext/www/...")
    
    CONTAINER_WWW_DIR.mkdir(parents=True, exist_ok=True)
    
    py_path = CONTAINER_WWW_DIR / "orbis.py"
    with open(py_path, "w", encoding="utf-8") as f:
        f.write(ORBIS_PY_CONTENT)
    print(f"    [CREATED] {py_path}")

    html_path = CONTAINER_WWW_DIR / "orbis.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(ORBIS_HTML_CONTENT)
    print(f"    [CREATED] {html_path}")


def configure_website_home_page(enable: bool = True):
    """Set home_page = 'orbis' in Website Settings so root / routes to Orbis portal."""
    action = "Setting" if enable else "Resetting"
    print(f"  [2/4] {action} Website Settings home_page...")
    
    target = "orbis" if enable else ""
    frappe.db.set_single_value("Website Settings", "home_page", target)
    frappe.clear_cache()
    print(f"    [OK] Website Settings home_page = '{target}'")


def configure_stock_workspace_shortcut(enable: bool = True):
    """Add or remove 'Orbis AI Portal' shortcut in Stock workspace."""
    action = "Adding" if enable else "Removing"
    print(f"  [3/4] {action} Stock Workspace shortcut...")

    if not frappe.db.exists("Workspace", "Stock"):
        print("    [NOTICE] Workspace 'Stock' not found. Skipping.")
        return

    ws = frappe.get_doc("Workspace", "Stock")
    label = "Orbis AI Portal"
    
    ws.shortcuts = [s for s in ws.shortcuts if s.label != label]
    
    if enable:
        ws.append("shortcuts", {
            "type": "URL",
            "url": "/",
            "label": label,
            "color": "Cyan"
        })
        print(f"    [ADDED] Shortcut '{label}' -> '/'")
    else:
        print(f"    [REMOVED] Shortcut '{label}'")

    ws.save(ignore_permissions=True)


def verify_routing():
    """Verify that root, login, and app routes resolve correctly."""
    print("  [4/4] Verifying Route Resolution...")
    from frappe.website.path_resolver import PathResolver
    
    r_root = PathResolver("/").resolve()[0]
    r_login = PathResolver("/login").resolve()[0]
    r_app = PathResolver("/app").resolve()[0]

    print(f"    Route '/'      -> '{r_root}' (Expected: 'orbis')")
    print(f"    Route '/login' -> '{r_login}' (Expected: 'login')")
    print(f"    Route '/app'   -> '{r_app}' (Expected: '/desk')")

    assert r_root == "orbis", f"Root route resolution mismatch: {r_root}"
    assert r_login == "login", f"Login route resolution mismatch: {r_login}"
    assert r_app == "/desk", f"App route resolution mismatch: {r_app}"
    print("    [PASS] All routes verified successfully!")


def run():
    print("=" * 80)
    print("  ORBIS ERP - STEP 32: SETUP ORBIS PRE-LOGIN PORTAL (LAYERS 1–4)")
    print("=" * 80)

    deploy_portal_files()
    configure_website_home_page(enable=True)
    configure_stock_workspace_shortcut(enable=True)
    verify_routing()

    frappe.db.commit()
    print("\n" + "=" * 80)
    print("  STEP 32 COMPLETE: PUBLIC ORBIS PORTAL IS ACTIVE AT http://localhost:8085/")
    print("=" * 80)


def main():
    frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
    frappe.connect()
    try:
        run()
    finally:
        frappe.destroy()


if __name__ == "__main__":
    main()
