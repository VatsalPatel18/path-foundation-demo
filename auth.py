import datetime
import os
from google.oauth2 import service_account
import google.auth.transport.requests
import json

def create_credentials() -> service_account.Credentials:
  secret_key_json = os.environ.get("SERVICE_ACC_KEY")
  if not secret_key_json:
    raise ValueError("Environment variable 'SERVICE_ACC_KEY' is not set or is empty.")
  try:
    service_account_info = json.loads(secret_key_json)
  except (SyntaxError, ValueError) as e:
    raise ValueError("Invalid service account key JSON format.") from e
  
  return service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
  )

def refresh_credentials(credentials: service_account.Credentials) -> service_account.Credentials:
    if credentials.expiry:
      expiry_time = credentials.expiry.replace(tzinfo=datetime.timezone.utc)

      # Calculate the time remaining until expiration
      time_remaining = expiry_time - datetime.datetime.now(datetime.timezone.utc)

      # Check if the token is about to expire (e.g., within 5 minutes)
      if time_remaining < datetime.timedelta(minutes=5):
          request = google.auth.transport.requests.Request()
          credentials.refresh(request) 
    else:
      request = google.auth.transport.requests.Request()
      credentials.refresh(request) 
    
    return credentials

def get_access_token_refresh_if_needed(credentials: service_account.Credentials) -> str:
    credentials = refresh_credentials(credentials)
    return credentials.token