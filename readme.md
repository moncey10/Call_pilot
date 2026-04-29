# 📞 Call Pilot — AI Call Screening & Summarization Assistant

> An intelligent call screening system that automatically answers calls, understands caller intent, flags urgent ones, transcribes conversations, and sends WhatsApp notifications — fully automated, zero manual steps.

## 🚀 What It Does
-  Screens incoming calls using LLM intent classification
-  Flags urgent calls for immediate attention
-  Handles call routing & recording via Twilio webhooks — zero manual steps
-  Transcribes calls using OpenAI Whisper
-  Generates structured summaries using GPT
-  Sends WhatsApp notifications for urgent calls
-  Logs all call data in SQLAlchemy database

## 🛠️ Tech Stack
| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI + Python |
| Voice Calls | Twilio Voice API |
| Transcription | OpenAI Whisper |
| Summarization | OpenAI GPT |
| Database | SQLAlchemy |
| Notifications | Twilio WhatsApp API |
| Architecture | Microservices + Webhooks |

## ⚙️ Setup
```bash
git clone https://github.com/moncey10/Call_pilot.git
cd Call_pilot
pip install -r requirements.txt
uvicorn main:app --reload
```

## 🔑 Environment Variables
```env
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
OPENAI_API_KEY=your_openai_key
WHATSAPP_TO=whatsapp:+91xxxxxxxxxx
```

## 👤 Author
**Moncey Patel** — AI/ML Engineer 
