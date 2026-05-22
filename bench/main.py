"""
Benchmarking script for evaluating the performance of different algorithms.
"""
from typing import Optional

from bench.settings import OPENAI_API_KEY, AMT_API_KEY
from bench.utils.amt_api import call_llm_chat, call_your_system
from bench.utils.mcq import format_prompt, benchmark_single_mcq, MCQItem, filter_cardiology_questions, categorize_mcq


# {"question": "A 15-year-old teenager presents for a sports physical. His blood pressure is 110/70 mm Hg, temperature is 36.5\u00b0C (97.7\u00b0F), and heart rate is 100/min. On cardiac auscultation, an early diastolic heart sound is heard over the cardiac apex while the patient is in the left lateral decubitus position. A transthoracic echocardiogram is performed which shows an ejection fraction of 60% without any other abnormalities. Which of the following is the end-systolic volume in this patient if his cardiac output is 6 L/min?", "answer": "40 mL", "options": {"A": "50 mL", "B": "60 mL", "C": "100 mL", "D": "40 mL", "E": "120 mL"}, "meta_info": "step1", "answer_idx": "D"}


def cardiac_output(heart_rate: int, stroke_volume: int) -> int:
    """
    Calculate cardiac output.
    :param heart_rate: int (beats per minute)
    :param stroke_volume: int (mL per beat)
    :return: int (mL per minute)
    """
    return heart_rate * stroke_volume

def ejection_fraction(stroke_volume: int, end_diastolic_volume: int) -> float:
    """
    Calculate ejection fraction.
    :param stroke_volume: int (mL)
    :param end_diastolic_volume: int (mL)
    :return: float (percentage)
    """
    return (stroke_volume / end_diastolic_volume) * 100

def stroke_volume(end_diastolic_volume: int, end_systolic_volume: int) -> int:
    """
    Calculate stroke volume.
    :param end_diastolic_volume: int (mL)
    :param end_systolic_volume: int (mL)
    :return: int (mL)
    """
    return end_diastolic_volume - end_systolic_volume

def stroke_volume_from_cardiac_output(cardiac_output: int, heart_rate: int) -> int:
    """
    Calculate stroke volume from cardiac output and heart rate.
    :param cardiac_output: int (mL per minute)
    :param heart_rate: int (beats per minute)
    :return: int (mL per beat)
    """
    return cardiac_output // heart_rate

def end_diastolic_volume(stroke_volume: int, ejection_fraction: float) -> int:
    """
    Calculate end-diastolic volume.
    :param stroke_volume: int (mL)
    :param ejection_fraction: float (percentage)
    :return: int (mL)
    """
    return int(stroke_volume / (ejection_fraction / 100))

def end_systolic_volume(end_diastolic_volume: int, stroke_volume: int) -> int:
    """
    Calculate end-systolic volume.
    :param end_diastolic_volume: int (mL)
    :param stroke_volume: int (mL)
    :return: int (mL)
    """
    return end_diastolic_volume - stroke_volume






from bench.settings import p

def load_and_filter_data(p: str):
    import json

    with open(p, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(data)} items from {p}")

    cardiology_data = filter_cardiology_questions(data)

    print(f"Filtered down to {len(cardiology_data)} cardiology questions")

    return cardiology_data



def filter_then_write():
    data = load_and_filter_data(p)

    with open('cardiology_data.jsonl', 'w', encoding='utf-8') as f:
        import json
        for item in data:
            f.write(json.dumps(item) + '\n')


####categorize_mcq('true_cardiology_data.jsonl', line_limit=-1)


from collections import Counter


def parse(el):
    import json
    try:
        custom_id = el.get('custom_id', '')
        return dict(custom_id=custom_id, **json.loads(el['response']['body']['choices'][0]['message']['content']))
    except:
        print("Error parsing:", el)
        return {"specialty": "Unknown", "rationale": "Parsing error or unexpected format."}


def filter_by_specialty(el):
    return el if el['specialty'] == 'Cardiology' else None

def filter_by_specialty(el):
    return el


def load_output(path: str):
    # C:\Users\Darren\Desktop\batch_68b314c81ca4819086d547df4302b2ec_output.jsonl

    # {"id": "batch_req_68b31de506fc8190a7105b9a81b146c9", "custom_id": "request-10178-5b484dc2-b1ed-58b0-98ff-f93b59596b38", "response": {"status_code": 200, "request_id": "00fc39941204cb0a49ef2041db73f78d", "body": {"id": "chatcmpl-CAHkLbY5E0dNofCvdxUB9MT2nvlbN", "object": "chat.completion", "created": 1756567533, "model": "gpt-4.1-nano-2025-04-14", "choices": [{"index": 0, "message": {"role": "assistant", "content": "{\"specialty\":\"OB/GYN\",\"rationale\":\"The question involves a pregnancy-related condition characterized by gross ultrasound findings and specific hCG levels, which is within the scope of obstetrics and gynecology.\"}", "refusal": null, "annotations": []}, "logprobs": null, "finish_reason": "stop"}], "usage": {"prompt_tokens": 485, "completion_tokens": 43, "total_tokens": 528, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 0, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}, "service_tier": "default", "system_fingerprint": "fp_38343a2f8f"}}, "error": null}
    import json

    with open(path, 'r', encoding='utf-8') as f:
        data = list(filter(filter_by_specialty, [parse(json.loads(line)) for line in f if line.strip()]))

    print(f"Loaded {len(data)} items from {path}")

    return data


subcategories = Counter()

data = load_output(r"C:\Users\Darren\Desktop\batch_68b32b88c1f481908d23f9700c3f6650_output.jsonl")

for item in data:
    subcategories[item.get('subcategory', 'Unknown')] += 1

print(subcategories)


quit()



def save():
    data = load_output(r"C:\Users\Darren\Desktop\batch_68b314c81ca4819086d547df4302b2ec_output.jsonl")

    with open('cardiology_data_from_output.jsonl', 'w', encoding='utf-8') as f:
        import json
        for item in data:
            f.write(json.dumps(item) + '\n')

def load_categorized_questions():
    import json

    output_path = "true_cardiology_data.jsonl"

    path_to_original_questions = p

    with open(path_to_original_questions, 'r', encoding='utf-8') as f:
        original_data = [json.loads(line) for line in f if line.strip()]

    path = r"cardiology_data_from_output.jsonl"

    with open(path, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f if line.strip()]

    print(len(data))

    questions = []

    for item in data:
        print(item)
        custom_id = item.get('custom_id', '')
        print("Custom ID:", custom_id)

        index = custom_id.split('-')[1]
        print(index)

        original_item = original_data[int(index)-1]

        print(original_item)

        questions.append(original_item)

    print(len(questions))

    with open(output_path, 'w', encoding='utf-8') as f:
        for item in questions:
            f.write(json.dumps(item) + '\n')




load_categorized_questions()






quit()


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



def framingham_risk_score(age: int, total_cholesterol: int, hdl_cholesterol: int, systolic_bp: int, is_smoker: bool, has_diabetes: bool) -> float:
    """
    Calculate the 10-year risk of coronary heart disease using the Framingham Risk Score.
    :param age: int
    :param total_cholesterol: int
    :param hdl_cholesterol: int
    :param systolic_bp: int
    :param is_smoker: bool
    :param has_diabetes: bool
    :return: float (risk percentage)
    """
    # This is a simplified version and may not reflect the actual Framingham Risk Score calculation.
    risk = 0
    risk += (age - 20) * 0.1
    risk += (total_cholesterol - hdl_cholesterol) * 0.02
    risk += (systolic_bp - 120) * 0.01
    if is_smoker:
        risk += 5
    if has_diabetes:
        risk += 3
    return min(max(risk, 0), 30)  # Risk capped between 0% and 30%


mermaid





### MIMIC ###

from settings import MIMIC_CSV_PATH

from bench.utils.mimic import extract, do_things

#do_things(MIMIC_CSV_PATH)
extracted = extract(MIMIC_CSV_PATH)



if __name__ == "__main__":
    asyncio.run(main())




quit()

import asyncio
from surrealdb import Surreal
from sentence_transformers import SentenceTransformer

# --- The New Patient Case ---
new_patient_summary = "A 67-year-old male with stable angina, hypertension, and well-managed type 2 diabetes. EGFR is 55, indicating moderate kidney disease. He is hesitant about invasive procedures."



if __name__ == "__main__":
    asyncio.run(main())



quit()


import enum

class ECGResult(enum.Enum):
    """
    Enum for ECG analysis results in bradycardia.
    """
    NORMAL = "Normal"
    SND = "Sinus Node Dysfunction"
    AV_BLOCK = "AV Block"
    CONDUCTION_DELAY = "Conduction Delay"



def ecg_image_analysis(image_path: str) -> str:
    """
    Placeholder function to analyze ECG image and return findings.
    :param image_path: str
    :return: str
    """
    # In a real implementation, this would involve image processing and analysis.
    return "The ECG shows atrial fibrillation with a rapid ventricular response."

def do_call(prompt_context: str, mcq_item: MCQItem) -> None:
    """
    Do a single call to the system with the given MCQ item.
    :param prompt_context: str
    :param mcq_item: MCQItem
    :return: None
    """
    prompt_to_send = format_prompt(prompt_context, mcq_item)
    model_response = call_your_system(prompt_to_send, AMT_API_KEY)

    print("MODEL RESPONSE", type(model_response), model_response)

    benchmark_single_mcq(mcq_item, model_response)



if __name__ == "__main__":
    # res = call_llm_chat(prompt="Hello, how are you?", openai_api_key=OPENAI_API_KEY, api_key=APT_API_KEY)
    # print(res)

    tools_prompt = "What tools do you have access to?"
    #res = call_llm_chat(prompt=tools_prompt, openai_api_key=OPENAI_API_KEY, api_key=AMT_API_KEY)
    #print(res)

    contraindications = dict(
        beta_blockers_contraindicated=None,
        digoxin_contraindicated=None,
        amiodarone_contraindicated=None
    )

    for option_key, option_text in TEST_OPTIONS.items():
        is_contraindicated = contraindication_checker(option_text.lower())
        if option_key == "A":
            contraindications['beta_blockers_contraindicated'] = is_contraindicated
        elif option_key == "E":
            contraindications['digoxin_contraindicated'] = is_contraindicated
        elif option_key == "D":
            contraindications['amiodarone_contraindicated'] = is_contraindicated

    mcq_item = MCQItem(
        question=TEST_QUESTION,
        options=TEST_OPTIONS,
        answer=f"{TEST_ANSWER}. {TEST_OPTIONS[TEST_ANSWER]}",
        answer_idx=TEST_ANSWER
    )

    print(contraindications)

    prompt_context = f"""
You are a medical expert system. You have access to the following information about drug contraindications:
Beta blockers contraindicated: {contraindications['beta_blockers_contraindicated']}
Digoxin contraindicated: {contraindications['digoxin_contraindicated']}
Amiodarone contraindicated: {contraindications['amiodarone_contraindicated']}
Use this information to help answer the following multiple-choice question.
    """

    do_call(prompt_context, mcq_item)





#test_data = load_test_data(p)
#print(len(test_data))


#benchmark_single_mcq(example_mcq)


# first 10

full_mcq_data = load_test_data_jsonl(p, n_lines=1_000)

cardiology_data = filter_cardiology_questions([item["question"] for item in full_mcq_data])

print(len(cardiology_data))




def do_things():
    for i, item in enumerate(full_mcq_data):
        print(f"Processing item: {i}")
        benchmark_single_mcq(item)



quit()


# ERROR - Error in ICD code prediction: NER extraction failed






def filter_only_first_task(item_id):
    item_id = item_id.replace('task', '')
    item_id_number, item_id_version = item_id.split('_')

    if int(item_id_version) == 1:
        return True
    return False


def do_stuff():
    for item in test_data:
        # dict_keys(['id', 'instruction', 'context', 'sol', 'eval_MRN'])
        item_id = item['id']
        if not filter_only_first_task(item_id):
            continue
        print(f"ID: {item_id}")
        print(f"Instruction: {item['instruction']}")
        print(f"Context: {item['context']}")

        sol = item.get('sol')
        print(f"Solution: {sol}")

        eval_mrn = item.get('eval_MRN')
        print(f"Eval MRN: {eval_mrn}")
