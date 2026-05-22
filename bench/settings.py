"""
Settings for benchmark tests.
"""
import dotenv

dotenv.load_dotenv()
import os



MIMIC_CSV_PATH = os.getenv("MIMIC_CSV_PATH", "data/mimic_data.csv")


API_URL = "http://localhost:3123"


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

AMT_API_KEY = os.getenv("AMT_API_KEY")

# http://localhost:3123/api/debug/session_v2
SESSION_TOKEN = os.getenv("SESSION_TOKEN")



p = r'D:\testing\work\dm\arsmedicatech-evals\MedAgentBench\data\medagentbench\test_data_v2.json'
p = r"C:\Users\Darren\Desktop\MAIN\currentz\amt\evals\train.jsonl"

