"""
Benchmarking script for evaluating the performance of different algorithms.
"""
from typing import Optional

from bench.settings import OPENAI_API_KEY, AMT_API_KEY
from bench.utils.amt_api import call_llm_chat


def get_session_token() -> Optional[str]:
    """
    Get a session token from the local debug API.
    :return: str or None
    """
    url = 'http://localhost:3123/api/debug/session_v2'
    import requests

    response = requests.post(url)

    if response.status_code == 200:
        data = response.json()
        return data['auth_token']
    return None


def get_key(session_token: str) -> str:
    """
    Get an API key from the local debug API using the session token.
    :param session_token: str
    :return: str
    """
    from bench.utils.amt_api import provision_api_key
    api_key = provision_api_key(session_token)
    return api_key


"""
1. Look up drug contraindications first.
2. Send context along with tool call request to MCP.
"""


TEST_QUESTION = """
Question:
A 62-year-old woman presents for a regular check-up. She complains of lightheadedness and palpitations which occur episodically.
Past medical history is significant for a myocardial infarction 6 months ago and NYHA class II chronic heart failure.
She also was diagnosed with grade I arterial hypertension 4 years ago.
Current medications are aspirin 81 mg, atorvastatin 10 mg, enalapril 10 mg, and metoprolol 200 mg daily.
Her vital signs are a blood pressure of 135/90 mm Hg, a heart rate of 125/min, a respiratory rate of 14/min, and a temperature of 36.5°C (97.7°F).
Cardiopulmonary examination is significant for irregular heart rhythm and decreased S1 intensity.
ECG is obtained and is shown in the picture (see image).
Echocardiography shows a left ventricular ejection fraction of 39%.
Which of the following drugs is the best choice for rate control in this patient?
"""

TEST_OPTIONS = {
    "A": "Atenolol",
    "B": "Verapamil",
    "C": "Diltiazem",
    "D": "Propafenone",
    "E": "Digoxin"
}

TEST_ANSWER = "E"



def contraindication_checker(drug_name: str) -> bool:
    """
    Placeholder function to check for contraindications
    :param drug_name: str
    :return: bool
    """
    contraindicated_drugs = ["atenolol", "verapamil", "diltiazem"]
    return drug_name in contraindicated_drugs



if __name__ == "__main__":
    # res = call_llm_chat(prompt="Hello, how are you?", openai_api_key=OPENAI_API_KEY, api_key=APT_API_KEY)
    # print(res)

    tools_prompt = "What tools do you have access to?"
    res = call_llm_chat(prompt=tools_prompt, openai_api_key=OPENAI_API_KEY, api_key=AMT_API_KEY)
    print(res)

