# main.py - FastAPI server, all Twilio webhooks live here

import os
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from twilio.rest import Client

from config import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER, MY_PHONE_NUMBER, BASE_URL
)
from Database import init_db, save_call, update_call, get_all_calls, get_call
from ai_agent import get_initial_greeting, process_speech, generate_summary, end_session
from call_manager import download_recording, get_recording_url

import json

app = FastAPI(title="AI Call Screener")

# Serve recordings as static files
os.makedirs("recordings", exist_ok=True)
app.mount("/recordings", StaticFiles(directory="recordings"), name="recordings")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


@app.on_event("startup")
def startup():
    init_db()
    print("[Server] AI Call Screener is running!")
    print(f"[Server] Set your Twilio webhook to: {BASE_URL}/incoming-call")


# ─────────────────────────────────────────────
# WEBHOOK 1: Incoming call starts
# ─────────────────────────────────────────────
@app.post("/incoming-call")
async def incoming_call(
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...)
):
    print(f"[Call] Incoming from {From} | SID: {CallSid}")

    # Save to DB
    save_call(call_sid=CallSid, caller_number=From)

    # Get AI greeting
    greeting = get_initial_greeting(CallSid)

    # Build TwiML response
    response = VoiceResponse()

    # Record the entire call
    response.record(
        action=f"{BASE_URL}/recording-complete",
        recording_status_callback=f"{BASE_URL}/recording-status",
        play_beep=False,
        timeout=1
    )

    # Gather speech from caller
    gather = Gather(
        input="speech",
        action=f"{BASE_URL}/handle-speech?call_sid={CallSid}",
        speech_timeout="auto",
        language="en-IN"
    )
    gather.say(greeting, voice="Polly.Aditi")
    response.append(gather)

    # Fallback if no speech detected
    response.redirect(f"{BASE_URL}/no-input?call_sid={CallSid}")

    return HTMLResponse(content=str(response), media_type="application/xml")


# ─────────────────────────────────────────────
# WEBHOOK 2: Handle caller's speech
# ─────────────────────────────────────────────
@app.post("/handle-speech")
async def handle_speech(
    request: Request,
    call_sid: str,
    SpeechResult: str = Form(default=""),
    Confidence: str = Form(default="0")
):
    print(f"[Speech] CallSID={call_sid} | Heard: '{SpeechResult}' | Confidence={Confidence}")

    response = VoiceResponse()

    if not SpeechResult.strip():
        # Nothing heard, ask again
        gather = Gather(
            input="speech",
            action=f"{BASE_URL}/handle-speech?call_sid={call_sid}",
            speech_timeout="auto",
            language="en-IN"
        )
        gather.say("I'm sorry, I didn't catch that. Could you please repeat?", voice="Polly.Aditi")
        response.append(gather)
        return HTMLResponse(content=str(response), media_type="application/xml")

    # Send to Claude AI
    result = process_speech(call_sid, SpeechResult)
    speech_text = result["speech"]
    action = result["action"]

    print(f"[AI] Response: '{speech_text}' | Action: {action}")

    if action == "transfer":
        # High urgency — transfer to owner
        response.say(speech_text, voice="Polly.Aditi")
        dial = Dial(action=f"{BASE_URL}/call-ended?call_sid={call_sid}&outcome=transferred")
        dial.number(MY_PHONE_NUMBER)
        response.append(dial)

        # Update DB
        update_call(
            call_sid,
            caller_name=result["caller_name"],
            call_reason=result["call_reason"],
            urgency=result["urgency"],
            outcome="transferred",
            transcript=result["messages"]
        )

    elif action == "block":
        # Spam/rude — end call
        response.say(speech_text, voice="Polly.Aditi")
        response.hangup()

        update_call(
            call_sid,
            caller_name=result["caller_name"],
            call_reason=result["call_reason"],
            urgency="low",
            outcome="spam_blocked",
            transcript=result["messages"]
        )
        _finalize_call(call_sid)

    elif action == "take_message":
        # Low/medium urgency — take message and end
        response.say(speech_text, voice="Polly.Aditi")
        response.hangup()

        update_call(
            call_sid,
            caller_name=result["caller_name"],
            call_reason=result["call_reason"],
            urgency=result["urgency"],
            outcome="voicemail",
            transcript=result["messages"]
        )
        _finalize_call(call_sid)

    else:
        # Conversation still ongoing — ask for more input
        gather = Gather(
            input="speech",
            action=f"{BASE_URL}/handle-speech?call_sid={call_sid}",
            speech_timeout="auto",
            language="en-IN"
        )
        gather.say(speech_text, voice="Polly.Aditi")
        response.append(gather)
        response.redirect(f"{BASE_URL}/no-input?call_sid={call_sid}")

    return HTMLResponse(content=str(response), media_type="application/xml")


# ─────────────────────────────────────────────
# WEBHOOK 3: No input fallback
# ─────────────────────────────────────────────
@app.post("/no-input")
async def no_input(call_sid: str):
    response = VoiceResponse()
    response.say("I didn't receive any input. Goodbye.", voice="Polly.Aditi")
    response.hangup()
    update_call(call_sid, outcome="no_input")
    return HTMLResponse(content=str(response), media_type="application/xml")


# ─────────────────────────────────────────────
# WEBHOOK 4: Call ended (after transfer)
# ─────────────────────────────────────────────
@app.post("/call-ended")
async def call_ended(call_sid: str, outcome: str = "completed"):
    response = VoiceResponse()
    _finalize_call(call_sid)
    return HTMLResponse(content=str(response), media_type="application/xml")


# ─────────────────────────────────────────────
# WEBHOOK 5: Recording ready
# ─────────────────────────────────────────────
@app.post("/recording-status")
async def recording_status(
    CallSid: str = Form(...),
    RecordingSid: str = Form(...),
    RecordingUrl: str = Form(...),
    RecordingStatus: str = Form(...)
):
    print(f"[Recording] Status={RecordingStatus} | SID={RecordingSid}")

    if RecordingStatus == "completed":
        # Download recording locally
        local_path = download_recording(RecordingSid, CallSid)
        update_call(
            CallSid,
            recording_url=RecordingUrl,
            recording_file=local_path
        )
    return {"status": "ok"}


@app.post("/recording-complete")
async def recording_complete():
    return HTMLResponse(content=str(VoiceResponse()), media_type="application/xml")


# ─────────────────────────────────────────────
# HELPER: Generate summary after call ends
# ─────────────────────────────────────────────
def _finalize_call(call_sid: str):
    """Generate Claude summary and clean up session."""
    call = get_call(call_sid)
    if not call:
        end_session(call_sid)
        return

    summary = generate_summary(
        call_sid=call_sid,
        caller_name=call.get("caller_name", "Unknown"),
        call_reason=call.get("call_reason", "Not specified"),
        urgency=call.get("urgency", "unknown"),
        outcome=call.get("outcome", "completed")
    )

    update_call(call_sid, summary=summary)
    end_session(call_sid)
    print(f"[Summary] Generated for {call_sid}: {summary[:80]}...")


# ─────────────────────────────────────────────
# DASHBOARD: View all calls
# ─────────────────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    calls = get_all_calls()

    rows = ""
    for c in calls:
        urgency_color = {
            "high": "#ef4444",
            "medium": "#f59e0b",
            "low": "#10b981"
        }.get(c.get("urgency", ""), "#6b7280")

        outcome_icon = {
            "transferred": "🔀",
            "voicemail": "📝",
            "spam_blocked": "🚫",
            "no_input": "🔇"
        }.get(c.get("outcome", ""), "❓")

        recording_html = ""
        if c.get("recording_file") and os.path.exists(c["recording_file"]):
            filename = os.path.basename(c["recording_file"])
            recording_html = f'<audio controls src="/recordings/{filename}" style="height:28px;width:180px;"></audio>'
        elif c.get("recording_url"):
            recording_html = f'<a href="{c["recording_url"]}" target="_blank" style="color:#00f5a0;">▶ Play</a>'

        rows += f"""
        <tr>
            <td>{c.get('created_at', '')[:16]}</td>
            <td style="font-family:monospace">{c.get('caller_number','—')}</td>
            <td><strong>{c.get('caller_name','—')}</strong></td>
            <td>{c.get('call_reason','—')}</td>
            <td style="color:{urgency_color};font-weight:700">{(c.get('urgency') or '—').upper()}</td>
            <td>{outcome_icon} {c.get('outcome','—')}</td>
            <td style="max-width:300px;font-size:12px;color:#aaa">{c.get('summary','—')}</td>
            <td>{recording_html}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>AI Call Screener Dashboard</title>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="15">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ background:#0a0a0f; color:#e8e8f0; font-family:'Segoe UI',sans-serif; padding:32px; }}
        h1 {{ font-size:28px; margin-bottom:6px; }}
        h1 span {{ color:#00f5a0; }}
        .subtitle {{ color:#6b6b8a; font-size:13px; margin-bottom:28px; }}
        .stats {{ display:flex; gap:16px; margin-bottom:28px; flex-wrap:wrap; }}
        .stat {{ background:#1a1a26; border:1px solid #2a2a3e; border-radius:10px; padding:16px 24px; }}
        .stat-num {{ font-size:28px; font-weight:800; color:#00f5a0; }}
        .stat-label {{ font-size:12px; color:#6b6b8a; margin-top:2px; }}
        table {{ width:100%; border-collapse:collapse; background:#12121a; border-radius:12px; overflow:hidden; border:1px solid #2a2a3e; }}
        th {{ background:#1a1a26; padding:12px 14px; text-align:left; font-size:11px; letter-spacing:1.5px; text-transform:uppercase; color:#6b6b8a; border-bottom:1px solid #2a2a3e; }}
        td {{ padding:12px 14px; border-bottom:1px solid #1a1a26; font-size:13px; vertical-align:top; }}
        tr:hover td {{ background:rgba(255,255,255,0.02); }}
        tr:last-child td {{ border-bottom:none; }}
    </style>
</head>
<body>
    <h1>AI Call <span>Screener</span></h1>
    <div class="subtitle">Auto-refreshes every 15 seconds &nbsp;·&nbsp; {len(calls)} total calls logged</div>

    <div class="stats">
        <div class="stat">
            <div class="stat-num">{len(calls)}</div>
            <div class="stat-label">Total Calls</div>
        </div>
        <div class="stat">
            <div class="stat-num" style="color:#ef4444">{sum(1 for c in calls if c.get('outcome')=='transferred')}</div>
            <div class="stat-label">Transferred</div>
        </div>
        <div class="stat">
            <div class="stat-num" style="color:#f59e0b">{sum(1 for c in calls if c.get('outcome')=='voicemail')}</div>
            <div class="stat-label">Voicemail</div>
        </div>
        <div class="stat">
            <div class="stat-num" style="color:#6b6b8a">{sum(1 for c in calls if c.get('outcome')=='spam_blocked')}</div>
            <div class="stat-label">Blocked</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Time</th>
                <th>Number</th>
                <th>Name</th>
                <th>Reason</th>
                <th>Urgency</th>
                <th>Outcome</th>
                <th>Summary</th>
                <th>Recording</th>
            </tr>
        </thead>
        <tbody>
            {rows if rows else '<tr><td colspan="8" style="text-align:center;padding:40px;color:#6b6b8a;">No calls yet. Waiting...</td></tr>'}
        </tbody>
    </table>
</body>
</html>"""
    return html


@app.get("/")
async def root():
    return {"status": "AI Call Screener running", "dashboard": "/dashboard"}