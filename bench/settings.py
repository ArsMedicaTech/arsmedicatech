"""
Settings for benchmark tests.
"""
import dotenv

dotenv.load_dotenv()
import os


API_URL = "http://localhost:3123"


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

AMT_API_KEY = os.getenv("AMT_API_KEY")

# http://localhost:3123/api/debug/session_v2
SESSION_TOKEN = os.getenv("SESSION_TOKEN")
