# AI call screening system using Twilio + FastAPI + OpenAI — auto-transcribes and summarizes calls

What It Does
Most businesses miss important calls or waste time on irrelevant ones. Call Pilot solves this by acting as an AI-powered receptionist that:

📲 Screens incoming calls — figures out why the person is calling using LLM intent classification
🚨 Flags urgent calls — automatically escalates high-priority calls for immediate attention
🔄 Handles routing & recording — manages call flow via Twilio webhooks with zero manual intervention
🗣️ Transcribes conversations — uses OpenAI Whisper for accurate speech-to-text
📝 Generates clean summaries — GPT writes a structured summary of every call
💬 Sends WhatsApp notifications — real-time alerts when urgent calls are flagged
🗄️ Logs everything — all call data stored in SQLAlchemy database for later review


## Terminal - 1
# uvicorn main:app --reload --port 8000

## Teminal - 2
# ngrok http 8000

## url to see established connection -> https://gibbosely-noneducative-suzy.ngrok-free.dev/incoming-call



