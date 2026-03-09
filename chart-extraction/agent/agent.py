import os
import json
import anthropic
from dotenv import load_dotenv
from agent.tools import TOOL_SCHEMAS, TOOL_MAP

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ANSI colors for terminal output
CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


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

    step = 0
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}Agent started for MRN: {mrn}{RESET}")
    print(f"{DIM}Variables: {', '.join(variables)}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    while True:
        step += 1
        print(f"{DIM}[Step {step}] Calling Claude...{RESET}")

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=system_prompt,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        # Append assistant turn to message history
        messages.append({"role": "assistant", "content": response.content})

        # Print any text blocks (the agent's "thinking")
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"\n{CYAN}[Agent thinking]{RESET}")
                print(f"{block.text.strip()}\n")

        # Agent finished without calling submit_extraction
        if response.stop_reason == "end_turn":
            print(f"\n{YELLOW}[Agent ended without submitting results]{RESET}\n")
            return {"mrn": mrn, "results": [], "error": "Agent ended without submitting results"}

        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                print(f"{YELLOW}[Tool call] {block.name}{RESET}({json.dumps(block.input, indent=2)})")

                # Route tool call to the correct function
                fn = TOOL_MAP[block.name]
                result = fn(**block.input)

                # submit_extraction is terminal — return immediately
                if block.name == "submit_extraction":
                    print(f"\n{GREEN}{BOLD}[Extraction complete]{RESET}")
                    for r in result["results"]:
                        confidence_color = GREEN if r.get("confidence") == "high" else YELLOW
                        print(f"  {r['variable']}: {r['value'][:80]} {confidence_color}[{r.get('confidence', '?')}]{RESET}")
                    print()
                    return {"mrn": mrn, "results": result["results"]}

                # Summarize tool result
                result_str = str(result)
                preview = result_str[:200] + "..." if len(result_str) > 200 else result_str
                print(f"{DIM}  → Result: {preview}{RESET}\n")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    result = run_extraction(
        "206919",
        "Retrospective review of medication management and clinical encounters",
        ["active_medications", "encounter_date", "encounter_type"],
    )
