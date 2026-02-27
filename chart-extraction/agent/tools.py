import base64
import logging
import requests
from fhir_client import fhir_client

logger = logging.getLogger(__name__)

# ── Section 1: Tool Functions ──────────────────────────────────────────────────


def fhir_fetch(mrn: str) -> dict:
    """Fetch all FHIR data for a patient by MRN."""
    # Resolve MRN to FHIR Patient ID
    patient_search = fhir_client.get("Patient", {"identifier": mrn})
    patient_id = patient_search["entry"][0]["resource"]["id"]

    result = {
        "patient_id": patient_id,
        "mrn": mrn,
        "medications": [],
        "conditions": [],
        "observations": [],
        "encounters": [],
        "documents": [],
    }

    # Fetch each resource type
    resource_map = {
        "medications": f"MedicationRequest?patient={patient_id}",
        "conditions": f"Condition?patient={patient_id}",
        "observations": f"Observation?patient={patient_id}",
        "encounters": f"Encounter?patient={patient_id}",
    }

    for key, endpoint in resource_map.items():
        try:
            resp = fhir_client.get(endpoint)
            result[key] = [e["resource"] for e in resp.get("entry", [])]
        except Exception as e:
            logger.warning(f"Failed to fetch {key} for patient {patient_id}: {e}")
            result[key] = []

    # Fetch DocumentReferences separately to extract metadata
    try:
        doc_resp = fhir_client.get(f"DocumentReference?patient={patient_id}")
        for entry in doc_resp.get("entry", []):
            resource = entry["resource"]
            result["documents"].append({
                "id": resource["id"],
                "date": resource.get("date", ""),
                "type": resource.get("type", {}).get("text", ""),
                "title": resource.get("description", resource.get("type", {}).get("text", "Unknown")),
            })
    except Exception as e:
        logger.warning(f"Failed to fetch documents for patient {patient_id}: {e}")
        result["documents"] = []

    return result


def get_document_content(document_id: str) -> str:
    """Retrieve the full text content of a clinical document by its FHIR DocumentReference ID."""
    try:
        doc = fhir_client.get(f"DocumentReference/{document_id}")
        attachment = doc["content"][0]["attachment"]

        if "url" in attachment:
            resp = requests.get(
                attachment["url"],
                headers={"Authorization": f"Bearer {fhir_client.access_token}"},
            )
            resp.raise_for_status()
            return resp.text
        elif "data" in attachment:
            return base64.b64decode(attachment["data"]).decode("utf-8")
        else:
            return "Document content unavailable"
    except Exception as e:
        logger.warning(f"Failed to get document {document_id}: {e}")
        return "Document content unavailable"


def submit_extraction(results: list) -> dict:
    """Terminal tool — returns results so the agent loop can intercept them."""
    return {"status": "complete", "results": results}


# ── Section 2: Tool Schemas ───────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "fhir_fetch",
        "description": "Fetch all FHIR data for a patient by MRN. Returns structured data including medications, conditions, observations, encounters, and a list of available documents with their IDs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mrn": {"type": "string", "description": "Patient MRN"}
            },
            "required": ["mrn"],
        },
    },
    {
        "name": "get_document_content",
        "description": "Retrieve the full text content of a clinical document by its FHIR DocumentReference ID. Use the document IDs returned by fhir_fetch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "FHIR DocumentReference ID from fhir_fetch results",
                }
            },
            "required": ["document_id"],
        },
    },
    {
        "name": "submit_extraction",
        "description": "Call this when you have finished extracting all variables or have exhausted all available data. This ends the extraction session and returns results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "variable": {
                                "type": "string",
                                "description": "Variable name as requested",
                            },
                            "value": {
                                "type": "string",
                                "description": "Extracted value, or 'NOT FOUND' if unavailable",
                            },
                            "source": {
                                "type": "string",
                                "description": "Document title or FHIR resource where value was found",
                            },
                            "confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                            },
                            "notes": {
                                "type": "string",
                                "description": "Any ambiguity, conflicts, or relevant context",
                            },
                        },
                        "required": ["variable", "value", "source", "confidence"],
                    },
                }
            },
            "required": ["results"],
        },
    },
]

# ── Section 3: Tool Router ────────────────────────────────────────────────────

TOOL_MAP = {
    "fhir_fetch": fhir_fetch,
    "get_document_content": get_document_content,
    "submit_extraction": submit_extraction,
}
