"""
Multiple Choice Question (MCQ) utilities for benchmarking.
"""
from typing import List, TypedDict, Dict, Any
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
    disease_keywords = [
        "myocardial infarction", "heart attack",
        "hypertension", "blood pressure",
        "heart failure", "CHF",
        "arrhythmia", "atrial fibrillation", "A-fib", "bradycardia", "tachycardia",
        "angina", "ischemia", "atherosclerosis",
        "cardiomyopathy", "endocarditis",
        "stenosis", "regurgitation"
    ]

    diagnostic_keywords = [
        "ECG", "EKG", "electrocardiogram",
        "echocardiogram", "echo",
        "stress test", "treadmill test",
        "catheterization", "angiogram",
        "troponin", "BNP", "lipid panel"
    ]

    medication_keywords = [
        "beta-blocker", "metoprolol",
        "ACE inhibitor", "lisinopril",
        "diuretic", "furosemide",
        "statin", "atorvastatin",
        "anticoagulant", "antiplatelet", "aspirin", "warfarin",
        "nitroglycerin", "digoxin"
    ]

    filtered_questions = []

    for question in questions:
        if any(keyword.lower() in question.lower() for keyword in disease_keywords) or \
           any(keyword.lower() in question.lower() for keyword in diagnostic_keywords) or \
           any(keyword.lower() in question.lower() for keyword in medication_keywords):
            filtered_questions.append(question)

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




#### TEST DATA ####

def format_prompt(item: MCQItem) -> str:
    """
    Format the prompt for the MCQ item.
    :param item: MCQItem - The MCQ item containing the question and options.
    :return: str - Formatted prompt string.
    """
    question_text = item["question"]
    options_text = "\n".join([f"{key}: {value}" for key, value in item["options"].items()])
    # Instruct the model to only return the letter of the correct option
    return f"Question: {question_text}\n\nOptions:\n{options_text}\n\nBased on the information, please choose the best option. Respond with only the letter of the correct option (e.g., A, B, C, D, or E)."


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
            if i >= n_lines:
                break
            data.append(json.loads(line.strip()))
        return data
