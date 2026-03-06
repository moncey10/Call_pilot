# # TWILIO_ACCOUNT_SID="AC56638b91d7d69ed751f8052194a057b2"
# TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# TWILIO_AUTH_TOKEN = "your_twilio_auth_token"
# ANTHROPIC_API_KEY = "sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# # TWILIO_AUTH_TOKEN="8e05f1e3130d2c74d3781e77411d59e5"



# TWILIO_PHONE_NUMBER = "+18317080045"   # Your Twilio number

# ANTHROPIC_API_KEY = "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"

# # Your real number - urgent calls will be transferred here
# MY_PHONE_NUMBER = "+919825374782"      # Your verified personal number

# # Server config
# # After running ngrok, paste the https URL here (without trailing slash)
# # Example: "https://abc123.ngrok.io"
# BASE_URL = "https://gibbosely-noneducative-suzy.ngrok-free.dev"

# # SQLite database file
# DB_FILE = "calls.db"

# # Recordings folder
# RECORDINGS_DIR = "recordings"

import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "ACxxxxxxxx")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_token")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "sk-ant-api03-xxx")

TWILIO_PHONE_NUMBER = "+18317080045"
MY_PHONE_NUMBER = "+919825374782"
BASE_URL = "https://gibbosely-noneducative-suzy.ngrok-free.dev"
DB_FILE = "calls.db"
RECORDINGS_DIR = "recordings"
