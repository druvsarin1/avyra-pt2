import os
import uuid
import time
import jwt
import requests
from dotenv import load_dotenv

load_dotenv()


class FHIRClient:
    def __init__(self):
        self.base_url = os.getenv("EPIC_BASE_URL")
        self.client_id = os.getenv("EPIC_CLIENT_ID")
        private_key_path = os.getenv("EPIC_PRIVATE_KEY_PATH")

        with open(private_key_path, "r") as f:
            self.private_key = f.read()

        self.access_token = None
        self.token_expiry = None

    def get_access_token(self):
        """Authenticate with Epic using SMART Backend Services (JWT assertion flow)."""
        # Token endpoint is at the server root, not under /api/FHIR/R4
        base = self.base_url.split("/api/")[0]
        token_url = f"{base}/oauth2/token"

        now = int(time.time())
        claims = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": token_url,
            "jti": str(uuid.uuid4()),
            "nbf": now,
            "iat": now,
            "exp": now + 240,  # 4 minutes
        }

        assertion = jwt.encode(
            claims,
            self.private_key,
            algorithm="RS384",
            headers={"kid": "chart-extraction-key-1"},
        )

        resp = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": assertion,
            },
        )
        resp.raise_for_status()

        data = resp.json()
        self.access_token = data["access_token"]
        self.token_expiry = now + data.get("expires_in", 300)

    def get(self, endpoint, params=None):
        """Make an authenticated GET request to the FHIR server."""
        if self.access_token is None or time.time() >= self.token_expiry:
            self.get_access_token()

        url = f"{self.base_url}/{endpoint}"
        resp = requests.get(
            url,
            params=params,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/fhir+json",
            },
        )
        resp.raise_for_status()
        return resp.json()


fhir_client = FHIRClient()
