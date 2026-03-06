# ai_agent.py - Claude AI handles the conversation logic

import anthropic
import json
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# In-memory store for ongoing call conversations
# { call_sid: { "messages": [], "caller_name": "", "call_reason": "", "urgency": "" } }
active_calls: dict = {}


SYSTEM_PROMPT = """You are an AI call screening assistant. Your job is to:
1. Greet the caller politely
2. Ask for their name
3. Ask the reason for their call
4. Based on the reason, determine urgency: low, medium, or high
5. Decide the action: transfer (high urgency), take_message (low/medium), or block (spam/rude)

Rules:
- Be professional, warm, and concise
- Keep responses SHORT (1-2 sentences max) since this is a phone call
- After collecting name and reason, output a JSON block ONLY in this exact format wrapped in <action> tags:
  <action>{"action": "transfer|take_message|block", "caller_name": "...", "call_reason": "...", "urgency": "low|medium|high"}</action>
- High urgency examples: emergency, urgent business, family emergency, doctor, boss
- Low urgency examples: sales, surveys, general inquiry, catching up
- Spam/block examples: robocalls, threatening, abusive language

Always respond in plain conversational English suitable for text-to-speech.
Do NOT use markdown, asterisks, or special characters in your speech responses.
"""


def get_or_create_session(call_sid: str) -> dict:
    if call_sid not in active_calls:
        active_calls[call_sid] = {
            "messages": [],
            "caller_name": None,
            "call_reason": None,
            "urgency": None,
            "action": None,
        }
    return active_calls[call_sid]


def process_speech(call_sid: str, caller_speech: str) -> dict:
    """
    Send caller's speech to Claude, get response.
    Returns: {
        "speech": "text to say to caller",
        "action": None | "transfer" | "take_message" | "block",
        "caller_name": str,
        "call_reason": str,
        "urgency": str
    }
    """
    session = get_or_create_session(call_sid)

    # Add caller message to history
    session["messages"].append({
        "role": "user",
        "content": caller_speech
    })

    # Call Claude
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=session["messages"]
    )

    assistant_text = response.content[0].text

    # Add Claude's response to history
    session["messages"].append({
        "role": "assistant",
        "content": assistant_text
    })

    # Check if Claude has made a decision (action tag present)
    action_data = None
    speech_text = assistant_text

    if "<action>" in assistant_text and "</action>" in assistant_text:
        # Extract the JSON action
        start = assistant_text.index("<action>") + len("<action>")
        end = assistant_text.index("</action>")
        action_json = assistant_text[start:end].strip()

        try:
            action_data = json.loads(action_json)
            session["caller_name"] = action_data.get("caller_name")
            session["call_reason"] = action_data.get("call_reason")
            session["urgency"] = action_data.get("urgency")
            session["action"] = action_data.get("action")

            # Remove the action tag from speech
            speech_text = assistant_text[:assistant_text.index("<action>")].strip()
            if not speech_text:
                # Generate a closing speech based on action
                if action_data["action"] == "transfer":
                    speech_text = "Please hold on, I am transferring your call now."
                elif action_data["action"] == "take_message":
                    speech_text = "Thank you. I have noted your message and the owner will get back to you soon. Goodbye."
                elif action_data["action"] == "block":
                    speech_text = "I'm sorry, I cannot assist with this call. Goodbye."
        except json.JSONDecodeError:
            pass

    return {
        "speech": speech_text,
        "action": action_data.get("action") if action_data else None,
        "caller_name": session.get("caller_name"),
        "call_reason": session.get("call_reason"),
        "urgency": session.get("urgency"),
        "messages": session["messages"]
    }


def get_initial_greeting(call_sid: str) -> str:
    """Generate the first greeting when call starts."""
    session = get_or_create_session(call_sid)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": "A new caller just connected. Greet them and ask for their name."
        }]
    )

    greeting = response.content[0].text

    # Store in session
    session["messages"].append({"role": "assistant", "content": greeting})

    return greeting


def generate_summary(call_sid: str, caller_name: str, call_reason: str, urgency: str, outcome: str) -> str:
    """Generate a written summary of the call after it ends."""
    session = active_calls.get(call_sid, {})
    transcript = session.get("messages", [])

    transcript_text = "\n".join([
        f"{'AI' if m['role'] == 'assistant' else 'Caller'}: {m['content']}"
        for m in transcript
        if "<action>" not in m["content"]
    ])

    prompt = f"""Generate a brief, professional written summary of this phone call screening.

Caller Name: {caller_name or 'Unknown'}
Reason for Call: {call_reason or 'Not specified'}
Urgency Level: {urgency or 'Unknown'}
Outcome: {outcome}

Transcript:
{transcript_text}

Write a 3-4 sentence summary covering: who called, why they called, urgency level, and what action was taken.
Be concise and professional."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text


def end_session(call_sid: str):
    """Clean up session after call ends."""
    if call_sid in active_calls:
        del active_calls[call_sid]