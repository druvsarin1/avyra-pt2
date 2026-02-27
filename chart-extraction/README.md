# Retrospective Chart Extraction

An AI-powered tool for extracting clinical variables from Epic EHR data using FHIR APIs and Claude.

## Project Structure

```
chart-extraction/
├── .env
├── .env.example
├── requirements.txt
├── README.md
├── fhir_client.py          ← Epic FHIR authentication & HTTP client
├── agent/
│   ├── tools.py             ← Tool functions, schemas, and router
│   └── agent.py             ← Agentic extraction loop
└── ui/
    └── app.py               ← Streamlit interface
```

## Setup

### 1. Install Dependencies

```bash
cd chart-extraction
pip install -r requirements.txt
```

### 2. Epic Sandbox Registration

1. Go to [open.epic.com](https://open.epic.com) → Sign Up → My Apps → Create New App
2. Set application type to **"Backend System"**
3. Generate an RSA key pair:
   ```bash
   openssl genrsa -out privatekey.pem 2048
   openssl rsa -in privatekey.pem -pubout -out publickey.pem
   ```
4. Paste the contents of `publickey.pem` into the app registration under **"Public Key"**
5. Copy the **Client ID** from the app dashboard into `.env`
6. Set `EPIC_PRIVATE_KEY_PATH=./privatekey.pem` in `.env`
7. Find sandbox test patient MRNs at [open.epic.com](https://open.epic.com) under the sandbox patient list

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:
```
EPIC_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
EPIC_CLIENT_ID=<your_client_id>
EPIC_PRIVATE_KEY_PATH=./privatekey.pem
ANTHROPIC_API_KEY=<your_anthropic_api_key>
```

## Usage

### Run the Streamlit UI

```bash
cd chart-extraction
streamlit run ui/app.py
```

### Test from CLI

```bash
cd chart-extraction
python -m agent.agent
```

## How It Works

1. **fhir_client.py** handles Epic authentication (SMART Backend Services JWT assertion flow) and provides a simple `get()` method for FHIR API calls.

2. **agent/tools.py** defines three tools:
   - `fhir_fetch` — pulls all structured data (medications, conditions, observations, encounters, documents) for a patient by MRN
   - `get_document_content` — retrieves full text of a clinical document by DocumentReference ID
   - `submit_extraction` — terminal tool that returns extracted results

3. **agent/agent.py** runs a Claude-powered agentic loop that:
   - Fetches patient data via FHIR
   - Searches structured data first, then clinical documents
   - Extracts each requested variable with value, source, confidence, and notes
   - Returns results when all variables are resolved or all sources exhausted

4. **ui/app.py** provides a Streamlit interface for entering study context, variables, and patient MRNs, then displays results in a table with CSV download.

## End-to-End Test

- **MRN**: Use an Epic sandbox patient MRN from open.epic.com
- **Study**: "Retrospective review of COVID-19 patients admitted in 2020 to assess treatment patterns and outcomes"
- **Variables**: `admission_date`, `discharge_date`, `remdesivir_administered`
- **Success criteria**: App returns a downloadable CSV with those three variables filled in with values and source documents for the test patient.
