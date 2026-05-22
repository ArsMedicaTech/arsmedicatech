"""
Utilities for processing the MIMIC dataset.
"""
from typing import Dict, Optional, List

import enum

class MIMICService(enum.Enum):
    """
    Enumeration of possible medical services in the MIMIC dataset.
    """
    MEDICINE = "MEDICINE"
    SURGERY = "SURGERY"
    ORTHOPAEDICS = "ORTHOPAEDICS"
    UROLOGY = "UROLOGY"
    NEUROSURGERY = "NEUROSURGERY"
    PLASTIC = "PLASTIC"
    OBGYN = "OBSTETRICS/GYNECOLOGY"
    CARDIOTHORACIC = "CARDIOTHORACIC"
    NEUROLOGY = "NEUROLOGY"
    PSYCHIATRY = "PSYCHIATRY"


def split_into_smaller_csvs(csv_path: str, chunk_size: int = 10_000) -> None:
    """
    Split a large CSV file into smaller CSV files.
    :param csv_path: str - Path to the original CSV file.
    :param chunk_size: int - Number of rows per smaller CSV file.
    """
    import pandas as pd

    df = pd.read_csv(csv_path, chunksize=chunk_size)
    for i, chunk in enumerate(df):
        chunk.to_csv(f'tmp/split_chunk_{i}.csv', index=False)


# note_id,input,target,input_tokens,target_tokens


def read_csv_to_dicts(csv_path: str) -> List[Dict[str, str]]:
    """
    Read a CSV file and convert each row to a dictionary.
    :param csv_path: str - Path to the CSV file.
    :return: list - A list of dictionaries representing the rows of the CSV file.
    """
    import csv

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]

    return data


MIMIC_KEYS = [
    '<SEX>',
    '<SERVICE>',
    '<ALLERGIES>',
    '<ATTENDING>',
    '<CHIEF COMPLAINT>',

    '<MAJOR SURGICAL OR INVASIVE PROCEDURE>',
    '<HISTORY OF PRESENT ILLNESS>',
    '<PAST MEDICAL HISTORY>',
    '<SOCIAL HISTORY>',
    '<FAMILY HISTORY>',

    '<PHYSICAL EXAM>',
    '<PERTINENT RESULTS>',
    '<MEDICATIONS ON ADMISSION>',

    '<DISCHARGE MEDICATIONS>',
    '<DISCHARGE DISPOSITION>',
    '<DISCHARGE DIAGNOSIS>',
    '<DISCHARGE CONDITION>',

    '<FOLLOWUP INSTRUCTIONS>',
    '<DISCHARGE INSTRUCTIONS>'
]


class History:
    """
    Represents the medical history section of a MIMIC record.
    """
    def __init__(self, major_procedures: str,
                 history_of_present_illness: str, past_medical_history: str,
                 social_history: str, family_history: str):
        self.major_procedures = major_procedures
        self.history_of_present_illness = history_of_present_illness
        self.past_medical_history = past_medical_history
        self.social_history = social_history
        self.family_history = family_history

    def d(self) -> Dict[str, str]:
        """
        Convert the History object to a dictionary.
        :return: dict - A dictionary representation of the History object.
        """
        return dict(
            major_procedures=self.major_procedures,
            history_of_present_illness=self.history_of_present_illness,
            past_medical_history=self.past_medical_history,
            social_history=self.social_history,
            family_history=self.family_history,
        )

class Discharge:
    """
    Represents the discharge section of a MIMIC record.
    """
    def __init__(self, medications: str, disposition: str, diagnosis: str, condition: str,
                 followup_instructions: str, discharge_instructions: str):
        self.medications = medications
        self.disposition = disposition
        self.diagnosis = diagnosis
        self.condition = condition
        self.followup_instructions = followup_instructions
        self.discharge_instructions = discharge_instructions

    def d(self) -> Dict[str, str]:
        """
        Convert the Discharge object to a dictionary.
        :return: dict - A dictionary representation of the Discharge object.
        """
        return dict(
            medications=self.medications,
            disposition=self.disposition,
            diagnosis=self.diagnosis,
            condition=self.condition,
            followup_instructions=self.followup_instructions,
            discharge_instructions=self.discharge_instructions,
        )

class MIMIC:
    def __init__(
            self,
            sex: chr,
            service: str,
            allergies: str,
            chief_complaint: str,
            history: History,
            discharge: Discharge,
            pertinent_results: str,
            medications_on_admission: str,
            attending: Optional[str] = None,
    ):
        self.sex = sex
        self.service = service
        self.allergies = allergies
        self.attending = attending
        self.chief_complaint = chief_complaint
        self.history = history
        self.discharge = discharge
        self.pertinent_results = pertinent_results
        self.medications_on_admission = medications_on_admission

    def d(self) -> Dict[str, Optional[str]]:
        """
        Convert the MIMIC object to a dictionary.
        :return: dict - A dictionary representation of the MIMIC object.
        """
        return dict(
            sex=self.sex,
            service=self.service,
            allergies=self.allergies,
            attending=self.attending,
            chief_complaint=self.chief_complaint,
            history=self.history.d(),
            discharge=self.discharge.d(),
            pertinent_results=self.pertinent_results,
            medications_on_admission=self.medications_on_admission,
        )


def parse_input(input_text: str) -> Dict[str, Optional[str]]:
    """
    Parse the input text to extract relevant fields.
    :param input_text: str - The input text to parse.
    :return: dict - A dictionary with parsed fields.
    """
    fields = {}
    for key in MIMIC_KEYS:
        start = input_text.find(key)
        if start != -1:
            start += len(key)
            end = input_text.find('<', start)
            if end == -1:
                end = len(input_text)
            fields[key] = input_text[start:end].strip()
        else:
            fields[key] = None
    return fields



def extract_specific_fields(row: Dict[str, str], *fields: str) -> Dict[str, Optional[str]]:
    """
    Extract specific fields from the input text.
    :param row: dict - The input text to parse.
    :param fields: str - The fields to extract.
    :return: dict - A dictionary with the extracted fields.
    """
    note_id = row.get('note_id', 'N/A')

    parsed_text = parse_input(row.get('input', ''))
    for field in fields:
        if field not in parsed_text:
            ...
        else:
            value = parsed_text[field]
            if value is None or value.strip() == '':
                print(f"WARNING: Field '{field}' is empty in note ID {note_id}.")
            else:
                ...

    return {field: parsed_text.get(field, None) for field in fields}


DESIRED_FIELDS = [
    '<SERVICE>',
    '<CHIEF COMPLAINT>',
    '<DISCHARGE DIAGNOSIS>',

    '<PERTINENT RESULTS>'
]

def extract(csv_path: str, desired_fields: List[str] = DESIRED_FIELDS) -> List[Dict[str, Optional[str]]]:
    """
    Extract specific fields from the MIMIC dataset CSV.
    :param csv_path: str - Path to the CSV file.
    :param desired_fields: list - List of fields to extract.
    :return: None
    """
    extracted = []
    for row in read_csv_to_dicts(csv_path):
        extracted_fields = extract_specific_fields(row, *desired_fields)
        extracted.append(extracted_fields)

    for extracted_row in extracted:
        print(f"Note ID: {extracted_row.get('note_id', 'N/A')}")
        for field in DESIRED_FIELDS:
            print(f"{field}: {extracted_row.get(field, 'N/A')}")
        print("-" * 40)

    return extracted



def do_things(csv_path: str):
    res = read_csv_to_dicts(csv_path)

    for row in res:
        print(f"Note ID: {row['note_id']}")
        print(f"Input: {row['input']}")
        print(f"Target: {row['target']}")
        print(f"Input Tokens: {row['input_tokens']}")
        print(f"Target Tokens: {row['target_tokens']}")

        print("Parsed Fields:")
        parsed_fields = parse_input(row['input'])
        for key, value in parsed_fields.items():
            print(f"{key}: {value if value is not None else 'N/A'}")

