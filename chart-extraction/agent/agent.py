import os
import anthropic
from dotenv import load_dotenv
from agent.tools import TOOL_SCHEMAS, TOOL_MAP

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def run_extraction(mrn: str, study_context: str, variables: list[str]) -> dict:
    """
    Run the extraction agent for a single patient.
    Returns a dict with mrn and list of extracted variable results.
    """

    system_prompt = f"""You are a medical data extraction specialist performing a retrospective chart review.

Study context:
{study_context}

Variables to extract:
{chr(10).join(f"- {v}" for v in variables)}

Instructions:
1. Start by calling fhir_fetch with the patient MRN to get all structured data and a list of available documents
2. Check structured FHIR data first — medications, conditions, observations — before opening documents
3. For variables not found in structured data, call get_document_content on relevant documents to search their text
4. For each variable record: the value you found, which document or resource it came from, and your confidence level
5. If a variable truly cannot be found after checking all available sources, record value as "NOT FOUND"
6. When all variables are resolved or all sources are exhausted, call submit_extraction with your complete results"""

    messages = [
        {"role": "user", "content": f"Please extract the requested variables for patient MRN: {mrn}"}
    ]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        # Append assistant turn to message history
        messages.append({"role": "assistant", "content": response.content})

        # Agent finished without calling submit_extraction
        if response.stop_reason == "end_turn":
            return {"mrn": mrn, "results": [], "error": "Agent ended without submitting results"}

        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                # Route tool call to the correct function
                fn = TOOL_MAP[block.name]
                result = fn(**block.input)

                # submit_extraction is terminal — return immediately
                if block.name == "submit_extraction":
                    return {"mrn": mrn, "results": result["results"]}

                # For all other tools, append result and continue loop
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })

            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    result = run_extraction(
        "sandbox-mrn",
        "COVID study",
        ["admission_date", "remdesivir_administered"],
    )
    print(result)
