"""
Multiple Choice Question (MCQ) utilities for benchmarking.
"""
from typing import List, TypedDict, Dict, Any, Optional
from pydantic import BaseModel
import json


class MCQQuestion(BaseModel):
    """
    Represents a multiple-choice question (MCQ) with its options and the correct answer.
    """
    question: str
    options: List[str]
    correct_answer: str


class MCQExplanation(BaseModel):
    """
    Represents an explanation for a multiple-choice question (MCQ) answer.
    """
    # tools_used: List[str]
    explanation: str


class MCQQuestionResponse(BaseModel):
    """
    Represents a response to a multiple-choice question (MCQ) including the selected answer and explanation.
    """
    answer: str
    # explanation: MCQExplanation
    explanation: str



example_mcq = {
    "question": "A 70-year-old man presented to a medical clinic for a routine follow-up. He has had hypertension for 20 years and is currently on multiple anti-hypertensive medications. The blood pressure is 150/100 mm Hg. The remainder of the examinations were within normal limits. Echocardiography showed some changes in the left ventricle. What is the most likely reason for the change?",
    "answer": "Increase in cardiac cell size",
    "options": {
        "A": "Disordered growth of the cardiac cells",
        "B": "Replacement of cardiac cells into stronger red fiber skeletal cells",
        "C": "Decrease in cardiac cell size",
        "D": "Increase in cardiac cell size",
        "E": "Increase in number of normal cardiac cells"
    },
    "answer_idx": "D"
}

class MCQItem(TypedDict):
    """
    Represents a multiple-choice question (MCQ) item with its question, answer, options, and the index of the correct answer.
    """
    question: str
    answer: str
    options: dict[str, str]
    answer_idx: str  # e.g., "A", "B", "C", "D", or "E"




#### FILTERING ####

# This process can be useful for segmenting datasets.
# This can help with reducing the test sample sizes for quicker iterations.
# This can also help with performing focused improvements in areas of known weakness.



def filter_cardiology_questions(questions: List[str]) -> List[str]:
    """
    Filters a list of questions to include only those related to cardiology based on specific keywords.
    :param questions: List of questions to filter.
    :return: List of questions related to cardiology.
    """
    keywords_to_filter_out = [
        "MRI", "CT scan", "renal", "hepatic", "carcinoma"
    ]

    disease_keywords = [
        "myocardial infarction", "heart attack",
        "hypertension",# "blood pressure",
        "heart failure", "CHF",
        "arrhythmia", "atrial fibrillation", "A-fib", "bradycardia", "tachycardia",
        "angina", "ischemia", "atherosclerosis",
        "cardiomyopathy", "endocarditis",
        "stenosis", "regurgitation"
    ]

    diagnostic_keywords = [
        "ECG", "EKG", "electrocardiogram",
        "echocardiogram",# "echo",
        "stress test", "treadmill test",
        "catheterization", "angiogram",
        "troponin", "BNP", "lipid panel"
    ]

    medication_keywords = [
        "beta-blocker", "metoprolol",
        "ACE inhibitor", "lisinopril",
        "diuretic", "furosemide",
        "statin", "atorvastatin",
        "anticoagulant", "antiplatelet",# "aspirin",
        "warfarin", "nitroglycerin", "digoxin"
    ]

    def accept(question):
        return any(keyword.lower() in question.lower() for keyword in disease_keywords) or \
        any(keyword.lower() in question.lower() for keyword in diagnostic_keywords) or \
        any(keyword.lower() in question.lower() for keyword in medication_keywords)

    def deny(question):
        return any(keyword.lower() in question.lower() for keyword in keywords_to_filter_out)

        return not deny(question) and accept(question)

    filtered_questions = []

    for question_dict in questions:
        question = json.dumps(question_dict)
        if accept(question) and not deny(question):
            #  "meta_info": "step2&3",
            print(question_dict['meta_info'])
            if question_dict['meta_info'] == 'step2&3':
                filtered_questions.append(question_dict)


    return filtered_questions





#### BENCHMARK ####

def benchmark_single_mcq(mcq_item: MCQItem, model_response: Dict[str, Any]) -> None:
    """
    Benchmark a single MCQ item against the model's response.
    :param mcq_item: MCQItem - The MCQ item containing the question, options, and correct answer index.
    :param model_response: Dict[str, Any] - The model's response containing the selected answer.
    :return: None
    """
    correct_answer_letter = mcq_item["answer_idx"]

    answer = model_response.get('answer')

    if not answer:
        print("Model did not return a valid answer.")
        return

    print(f"System responded with: {answer}")
    print(f"Correct answer is: {correct_answer_letter}")

    if answer == correct_answer_letter:
        print("✅ Result: Correct")
    else:
        print("❌ Result: Incorrect")

    i = input("Press Enter to continue to the next MCQ or type 'exit' to quit: ")
    if i.lower() == 'exit':
        print("Exiting the benchmark.")
        return




#PROMPT_SUFFIX = "Respond with only the letter of the correct option (e.g., A, B, C, D, or E)."
PROMPT_SUFFIX = "Please respond with an explanation and any tool calls used (and their outputs). You should have relevant tools available at your disposal and it is imperative that you use them when available for sake of not only accuracy but also auditability and explainability."

#### TEST DATA ####

def format_prompt(prompt_context: str, item: MCQItem) -> str:
    """
    Format the prompt for the MCQ item.
    :param prompt_context: str - Additional context or instructions for the prompt.
    :param item: MCQItem - The MCQ item containing the question and options.
    :return: str - Formatted prompt string.
    """
    question_text = item["question"]
    options_text = "\n".join([f"{key}: {value}" for key, value in item["options"].items()])
    # Instruct the model to only return the letter of the correct option
    return f"Additional Context:\n{prompt_context}\n\nQuestion: {question_text}\n\nOptions:\n{options_text}\n\nBased on the information, please choose the best option.\n\n{PROMPT_SUFFIX}"


def load_test_data(file_path: str) -> Dict[str, Any]:
    """
    Load test data from a JSON file.
    :param file_path: str - Path to the JSON file containing test data.
    :return: dict - Parsed JSON data.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_test_data_jsonl(file_path: str, n_lines: int) -> List[Dict[str, Any]]:
    """
    Load test data from a JSON Lines file.
    :param file_path: str - Path to the JSON Lines file containing test data.
    :param n_lines: int - Number of lines to read from the file.
    :return: list - List of parsed JSON objects.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = []
        for i, line in enumerate(f):
            if n_lines != -1 and i >= n_lines:
                break
            data.append(json.loads(line.strip()))
        return data


import uuid
import enum

class GPTModel(enum.Enum):
    """
    Enum class for GPT model identifiers.
    """
    GPT_4_1_NANO = "gpt-4.1-nano-2025-04-14"

    def __str__(self):
        return self.value

class Batch:
    """
    Represents a batch request for the GPT model API.
    """
    def __init__(
            self, model: GPTModel, system_prompt: str, user_prompt: str, max_tokens: int = 1000,
            response_format: Optional[Dict[str, Any]] = None, id_prefix: str = None
    ):
        self.model = model
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.max_tokens = max_tokens
        self.response_format = response_format
        self.id_prefix = id_prefix

    def hash_user_prompt(self) -> str:
        """
        Generate a unique hash for the user prompt using UUID5.
        :return: str - Unique hash string.
        """
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, self.user_prompt))

    @property
    def custom_id(self) -> str:
        """
        Generate a custom ID for the batch based on the hashed user prompt.
        :return: str - Custom ID string.
        """
        return f"request-{self.id_prefix if self.id_prefix else 'x'}-{self.hash_user_prompt()}"

    def d(self) -> Dict[str, Any]:
        """
        Convert the batch to a dictionary format suitable for API requests.
        :return: dict - Dictionary representation of the batch.
        """
        return dict(
            custom_id=self.custom_id,
            method="POST",
            url="/v1/chat/completions",
            body={
                "model": str(self.model),
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self.user_prompt}
                ],
                "max_tokens": self.max_tokens,
                **({"response_format": self.response_format} if self.response_format else {})
            }
        )
# {"custom_id": "request-1", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-3.5-turbo-0125", "messages": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "Hello world!"}], "max_tokens": 1000}}


SYSTEM_PROMPT = """
You are tasked with categorizing the following medical knowledge multiple choice questions by the specialty they belong to. The specialties are as follows:
* Cardiology.
* Neurology.
* Psychiatry.
* OB/GYN.
* Gastroenterology.
* Endocrinology.
* Other.
* Unsure/Multiple.

If there is any ambiguity, you may provide an optional (very brief) rationale as well.
"""

# * Pulmonology.
# * Nephrology.
# * Dermatology.
# * Rheumatology.

response_format = dict(
    type="json_schema",
    json_schema=dict(
        name="mcq_specialty_categorization",
        strict=True,
        schema=dict(
            type="object",
            properties=dict(
                specialty=dict(
                    type="string",
                    description="The medical specialty that the question belongs to. Must be one of: Cardiology, Neurology, Psychiatry, OB/GYN, Gastroenterology, Endocrinology, Other, Unsure/Multiple.",
                    enum=["Cardiology", "Neurology", "Psychiatry", "OB/GYN", "Gastroenterology", "Endocrinology", "Other", "Unsure/Multiple"]
                ),
                rationale=dict(
                    type="string",
                    description="Optional rationale for the chosen specialty categorization. Provide this only if there is ambiguity or multiple specialties could apply."
                )
            ),
            required=["specialty", "rationale"],
            additionalProperties=False,
            description="Schema for categorizing medical knowledge multiple choice questions by specialty."
        )
    )
)



CARDIOLOGY_SUBCATEGORIES = """
You are tasked with categorizing medical knowledge multiple choice questions into subcategories. They are already categorized as cardiology questions.

The 5 Core Cardiology Categories
________________________________

1. Ischemic Heart Disease (The "Pipes")
This category covers everything related to the coronary arteries—the pipes that supply blood to the heart muscle itself. Questions here focus on blockages and lack of blood flow (ischemia).
Includes: Myocardial Infarction (heart attacks), Acute Coronary Syndromes (ACS), chronic stable angina, coronary artery disease (CAD), and procedures like stents (PCI) and bypass surgery (CABG).

2. Heart Failure & Cardiomyopathies (The "Pump")
This category is for questions about the heart muscle's ability to function as a pump. It covers conditions where the pump is either too weak (systolic failure) or too stiff (diastolic failure), as well as diseases of the muscle itself.
Includes: Heart Failure with Reduced or Preserved Ejection Fraction (HFrEF/HFpEF), Guideline-Directed Medical Therapy (GDMT) for HF, and cardiomyopathies (e.g., hypertrophic, dilated).

3. Arrhythmias & Electrophysiology (The "Wiring")
This is the heart's electrical system. Any question centered on the rate or rhythm of the heartbeat belongs here.
Includes: Atrial Fibrillation (AFib), bradycardia (slow heart rates), tachycardia (fast heart rates), palpitations, sudden cardiac death, and devices like pacemakers and defibrillators (ICDs).

4. Valvular & Structural Disease (The "Valves & Doors")
This category deals with the physical structures of the heart, primarily its four valves, but also includes other structural issues.
Includes: Aortic stenosis, mitral regurgitation, endocarditis (valve infections), congenital heart defects in adults (like atrial septal defects), and pericardial disease.

5. Vascular Medicine & Prevention (The "System")
This is a broad but crucial category for questions about the health of the entire circulatory system and the primary risk factors that damage it. If the question is about preventing future events or about blood vessels outside the heart, it goes here.
Includes: Hypertension (HTN), dyslipidemia (cholesterol management), primary/secondary prevention strategies, peripheral artery disease (PAD), and aortic diseases (aneurysms, dissections).

6. Other/Unsure
If there are any that that are truly difficult to categorize, or constitute rare edge cases, or if you simply aren't sure, then you may categorize them as "Other/Unsure".

____________________
Handling Overlap
____________________

The main challenge in any categorization is overlap. For example, a heart attack (Ischemic category) is the most common cause of Heart Failure. A patient with Heart Failure often develops Atrial Fibrillation.

To maintain a clean separation for your script, use this simple rule:
Categorize based on the primary focus of the question being asked.
If the question is about managing chest pain or a blocked artery, it's Ischemic Heart Disease.
If the question is about managing shortness of breath and fluid overload due to a weak heart muscle (even if caused by ischemia), it's Heart Failure.
If the question is about identifying or treating an irregular heartbeat (even in a patient with heart failure), it's Arrhythmias.
"""

cardiology_response_format = dict(
    type="json_schema",
    json_schema=dict(
        name="mcq_cardiology_subcategory_categorization",
        strict=True,
        schema=dict(
            type="object",
            properties=dict(
                subcategory=dict(
                    type="string",
                    description="The cardiology subcategory that the question belongs to. Must be one of: Ischemic Heart Disease, Heart Failure & Cardiomyopathies, Arrhythmias & Electrophysiology, Valvular & Structural Disease, Vascular Medicine & Prevention.",
                    enum=["Ischemic Heart Disease", "Heart Failure & Cardiomyopathies", "Arrhythmias & Electrophysiology", "Valvular & Structural Disease", "Vascular Medicine & Prevention", "Other/Unsure"]
                ),
                rationale=dict(
                    type="string",
                    description="Optional rationale for the chosen cardiology subcategory categorization. Especially important if there is any serious ambiguity."
                )
            ),
            required=["subcategory", "rationale"],
            additionalProperties=False,
            description="Schema for categorizing cardiology multiple choice questions by subcategory."
        )
    )
)


def create_batch(input_jsonl_path: str, line_limit: int = -1, output_jsonl_path: str = "batchinput.jsonl", write: bool = True) -> List[Batch]:
    """
    Create a list of Batch objects from the input JSON Lines file.
    :param input_jsonl_path: str - Path to the JSON Lines file containing MCQ items.
    :param line_limit: int - Limit the number of lines to process from the input file. Default is -1 (no limit).
    :param output_jsonl_path: str - Path to the output JSON Lines file to write the batch data.
    :return: list - List of Batch objects.
    """
    test_data = load_test_data_jsonl(input_jsonl_path, n_lines=line_limit)

    batches = []
    for i, item in enumerate(test_data):
        user_prompt = str(item)
        batch = Batch(
            model=GPTModel.GPT_4_1_NANO,
            system_prompt=CARDIOLOGY_SUBCATEGORIES,
            user_prompt=user_prompt,
            response_format=cardiology_response_format,
            max_tokens=1_000,
            id_prefix=f"{i+1}"
        )
        batches.append(batch)

    if write:
        with open(output_jsonl_path, 'w', encoding='utf-8') as f:
            for batch in batches:
                f.write(json.dumps(batch.d()) + "\n")

    return batches


def categorize(input_file: str = "batchinput.jsonl") -> str:
    """
    Create a batch file for processing multiple MCQs using the OpenAI API.
    :param input_file: str - Path to the input JSON Lines file containing MCQ items.
    :return: str - ID of the created batch input file.
    """
    from openai import OpenAI
    client = OpenAI()

    batch_input_file = client.files.create(
        file=open(input_file, "rb"),
        purpose="batch"
    )

    print(batch_input_file)

    batch_input_file_id = batch_input_file.id

    batch = client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            #"description": "Batch categorization of medical MCQs by specialty",
            "description": "Batch categorization of cardiology MCQs by subcategory",
        }
    )

    return batch.id


class BatchStatus(enum.Enum):
    """
    Enum class for batch job statuses.
    """
    VALIDATING = "validating"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"

    def __str__(self):
        return self.value

def poll_for_status(batch_id: str) -> BatchStatus:
    """
    Poll the status of a batch job until it is completed.
    :param batch_id: str - ID of the batch job to poll.
    :return: BatchStatus - Final status of the batch job.
    """
    import time

    from openai import OpenAI
    client = OpenAI()

    while True:
        batch = client.batches.retrieve(batch_id)
        print(f"Batch ID: {batch.id}, Status: {batch.status}")
        time.sleep(60)

        if batch.status.lower() in ["completed", "failed"]:
            break

    return batch.status



def categorize_mcq(path_to_input_jsonl: str, line_limit = 100) -> None:
    """
    Main function to create a batch, categorize MCQs, and poll for status.
    :param path_to_input_jsonl: str - Path to the input JSON Lines file containing MCQ items.
    :param line_limit: int - Limit the number of lines to process from the input file. Default is 100.
    :return: None
    """
    create_batch(input_jsonl_path=path_to_input_jsonl, line_limit=line_limit)
    batch_id = categorize()
    poll_for_status(batch_id=batch_id)


# 100 took 2 mins.
# 1000 should take 20 mins.
