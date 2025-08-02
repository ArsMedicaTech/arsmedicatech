"""
Patient routes for managing patient data and encounters.
"""
import json
from typing import Any, Dict, List, Tuple, Union

from flask import Response, jsonify, request

from lib.data_types import PatientID
from lib.db.surreal import DbController
from lib.models.patient.main import (create_encounter, create_patient,
                                     delete_encounter, delete_patient,
                                     get_all_encounters, get_all_patients,
                                     get_encounter_by_id,
                                     get_encounters_by_patient,
                                     get_patient_by_id,
                                     search_encounter_history,
                                     search_patient_history, serialize_patient,
                                     update_encounter, update_patient)
from lib.services.auth_decorators import get_current_user
from lib.services.icd_autocoder_service import ICDAutoCoderService
from settings import logger


def patch_intake_route(patient_id: PatientID) -> Tuple[Response, int]:
    """
    API endpoint to patch a patient's intake data.
    :param patient_id: The ID of the patient to update, formatted as 'Patient:{patient_id}'.
    :return: Response indicating success or failure.
    """
    payload = request.get_json()
    logger.debug(f"Patching patient {patient_id} with payload: {payload}")

    # Map 'User:' to patient ID if needed
    patient_id = PatientID(patient_id.replace('User:', ''))

    result = update_patient(patient_id, payload)
    logger.debug(f"Update result: {result}")
    if not result:
        logger.error(f"Failed to update patient {patient_id}: {result}")
        return jsonify({"error": "Failed to update patient"}), 400
    return jsonify({'ok': True}), 200


def search_patients_route() -> Tuple[Response, int]:
    """
    API endpoint to search patient histories via FTS.
    Accepts a 'q' query parameter.
    e.g., /api/patients/search?q=headache

    :return: JSON response with search results or error message.
    """
    search_term = request.args.get('q', '')
    if not search_term or len(search_term) < 2:
        return jsonify({"message": "Please provide a search term with at least 2 characters."}), 400

    results = search_patient_history(search_term)
    return jsonify(results), 200

def search_encounters_route() -> Tuple[Response, int]:
    """
    API endpoint to search encounters via FTS.
    Accepts a 'q' query parameter.
    e.g., /api/encounters/search?q=headache

    :return: JSON response with search results or error message.
    """
    search_term = request.args.get('q', '')
    if not search_term or len(search_term) < 2:
        return jsonify({"message": "Please provide a search term with at least 2 characters."}), 400
    
    results = search_encounter_history(search_term)
    return jsonify(results), 200


def patient_endpoint_route(patient_id: PatientID) -> Tuple[Response, int]:
    """
    API endpoint to handle patient-related operations.
    :param patient_id: The ID of the patient to operate on, formatted as 'Patient:{patient_id}'.
    :return: Response with patient data or error message.
    """
    logger.debug(f"Patient endpoint called with patient_id: {patient_id}")
    logger.debug(f"Request method: {request.method}")

    if request.method == 'GET':
        # Get a specific patient
        logger.debug(f"Getting patient with ID: {patient_id}")
        patient = get_patient_by_id(patient_id)
        logger.debug(f"Patient result: {patient}")
        if patient:
            patient = serialize_patient(patient)
            return jsonify(patient), 200
        else:
            return jsonify({"error": "Patient not found"}), 404

    elif request.method == 'PUT':
        # Update a patient
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        patient = update_patient(patient_id, data)
        if patient:
            return jsonify(patient), 200
        else:
            return jsonify({"error": "Patient not found or update failed"}), 404

    elif request.method == 'DELETE':
        # Delete a patient
        result = delete_patient(patient_id)
        if result:
            return jsonify({"message": "Patient deleted successfully"}), 200
        else:
            return jsonify({"error": "Patient not found or delete failed"}), 404

    else:
        logger.error(f"Unknown method {request.method} for patient endpoint")
        return jsonify({"error": "Method not allowed"}), 405


def patients_endpoint_route() -> Tuple[Response, int]:
    """
    API endpoint to handle patient-related operations.
    :return: JSON response with patient data or error message.
    """
    if request.method == 'GET':
        # Get all patients
        patients = get_all_patients()
        return jsonify(patients), 200
    elif request.method == 'POST':
        # Create a new patient
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        patient = create_patient(data)
        if patient:
            return jsonify(patient), 201
        else:
            return jsonify({"error": "Failed to create patient"}), 500
    else:
        logger.error(f"Unknown method {request.method} for patients endpoint")
        return jsonify({"error": "Method not allowed"}), 405


def get_all_encounters_route() -> Tuple[Response, int]:
    """
    API endpoint to get all encounters

    :return: JSON response with all encounters or error message.
    """
    try:
        encounters = get_all_encounters()
        return jsonify(encounters), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_encounters_by_patient_route(patient_id: PatientID) -> Tuple[Response, int]:
    """
    API endpoint to get all encounters for a specific patient

    :param patient_id: The ID of the patient to get encounters for, formatted as 'Patient:{patient_id}'.
    :return: JSON response with encounters or error message.
    """
    try:
        encounters = get_encounters_by_patient(patient_id)
        return jsonify(encounters), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_encounter_by_id_route(encounter_id: str) -> Tuple[Response, int]:
    """
    API endpoint to get a specific encounter by ID

    :param encounter_id: The ID of the encounter to retrieve.
    :return: JSON response with the encounter or error message.
    """
    try:
        encounter = get_encounter_by_id(encounter_id)
        if encounter:
            return jsonify(encounter), 200
        else:
            return jsonify({"error": "Encounter not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def create_encounter_route(patient_id: PatientID) -> Tuple[Response, int]:
    """
    API endpoint to create a new encounter for a patient

    :param patient_id: The ID of the patient to create an encounter for, formatted as 'Patient:{patient_id}'.
    :return: JSON response with the created encounter or error message.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        if not data.get("provider_id"):
            return jsonify({"error": "provider_id is required"}), 400
        
        # Set default date if not provided
        if not data.get("date_created"):
            from datetime import datetime
            data["date_created"] = datetime.now().isoformat()
        
        encounter = create_encounter(data, patient_id)
        if encounter:
            return jsonify(encounter), 201
        else:
            return jsonify({"error": "Failed to create encounter"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def update_encounter_route(encounter_id: str) -> Tuple[Response, int]:
    """
    API endpoint to update an encounter

    :param encounter_id: The ID of the encounter to update.
    :return: JSON response with the updated encounter or error message.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        encounter = update_encounter(encounter_id, data)
        if encounter:
            return jsonify(encounter), 200
        else:
            return jsonify({"error": "Encounter not found or update failed"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def delete_encounter_route(encounter_id: str) -> Tuple[Response, int]:
    """
    API endpoint to delete an encounter

    :param encounter_id: The ID of the encounter to delete.
    :return: JSON response indicating success or failure.
    """
    try:
        success = delete_encounter(encounter_id)
        if success:
            return jsonify({"message": "Encounter deleted successfully"}), 200
        else:
            return jsonify({"error": "Encounter not found or delete failed"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def extract_entities_from_notes_route() -> Tuple[Response, int]:
    """
    Extract entities and ICD codes from encounter notes using the ICD autocoder service.
    
    This endpoint processes the note_text from an encounter to extract medical entities,
    normalize them using UMLS, and match them to ICD-10-CM codes.
    
    Expected request body:
    {
        "note_text": "string or SOAP notes object",
        "note_type": "soap" or "text"
    }
    
    Returns:
    {
        "entities": [...],
        "normalized_entities": [...],
        "icd_codes": [...]
    }
    """
    try:
        data = request.get_json()
        if not data or 'note_text' not in data:
            return jsonify({"error": "note_text is required"}), 400
        
        note_text = data.get('note_text')
        note_type = data.get('note_type', 'text')
        
        # Convert SOAP notes to plain text if needed
        if note_type == 'soap' and isinstance(note_text, dict):
            # Extract text from SOAP notes
            soap_sections = []
            if note_text.get('subjective'):
                soap_sections.append(f"Subjective: {note_text['subjective']}")
            if note_text.get('objective'):
                soap_sections.append(f"Objective: {note_text['objective']}")
            if note_text.get('assessment'):
                soap_sections.append(f"Assessment: {note_text['assessment']}")
            if note_text.get('plan'):
                soap_sections.append(f"Plan: {note_text['plan']}")
            
            # Join all sections with newlines
            text_to_process = '\n\n'.join(soap_sections)
        else:
            # Use plain text as is
            text_to_process = str(note_text) if note_text else ""
        
        if not text_to_process.strip():
            return jsonify({"error": "No text content to process"}), 400
        
        # Process the text with ICD autocoder service
        autocoder = ICDAutoCoderService(text_to_process)
        result = autocoder.main()
        
        logger.debug(f"ICD autocoder result: {result}")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in extract_entities_from_notes_route: {e}")
        return jsonify({"error": f"Failed to process notes: {str(e)}"}), 500


def get_cache_stats_route() -> Tuple[Response, int]:
    """
    Get entity cache statistics.
    
    Returns:
    {
        "total_cached_entities": 123,
        "cache_enabled": true
    }
    """
    try:
        from lib.services.cache_service import EntityCacheService
        db = DbController()
        stats = EntityCacheService.get_cache_stats(db)
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({"error": "An internal error has occurred."}), 500
