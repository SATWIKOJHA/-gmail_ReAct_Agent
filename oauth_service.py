"""
OAuth Service Module
Handles Google OAuth 2.0 authentication and Gmail API operations.
"""

import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple, List, Dict, Any, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# OAuth scopes for Gmail
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]


def create_oauth_flow(client_id: str, client_secret: str, redirect_uri: str) -> Flow:
    """
    Create an OAuth 2.0 flow for Google authentication.
    
    Args:
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        redirect_uri: Redirect URI after authentication
    
    Returns:
        OAuth Flow object
    """
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    
    return flow


def get_authorization_url(client_id: str, client_secret: str, redirect_uri: str) -> Tuple[str, str]:
    """
    Generate the Google OAuth authorization URL.
    
    Args:
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        redirect_uri: Redirect URI after authentication
    
    Returns:
        Tuple of (authorization_url, state)
    """
    flow = create_oauth_flow(client_id, client_secret, redirect_uri)
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    return authorization_url, state


def exchange_code_for_credentials(
    code: str, 
    client_id: str, 
    client_secret: str, 
    redirect_uri: str
) -> Tuple[bool, Any]:
    """
    Exchange authorization code for credentials.
    
    Args:
        code: Authorization code from Google
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        redirect_uri: Redirect URI
    
    Returns:
        Tuple of (success, credentials or error message)
    """
    try:
        flow = create_oauth_flow(client_id, client_secret, redirect_uri)
        flow.fetch_token(code=code)
        credentials = flow.credentials
        return True, credentials
    except Exception as e:
        return False, f"Failed to exchange code: {str(e)}"


def get_gmail_service(credentials: Credentials):
    """
    Create a Gmail API service from credentials.
    
    Args:
        credentials: Google OAuth credentials
    
    Returns:
        Gmail API service object
    """
    return build('gmail', 'v1', credentials=credentials)


def get_user_email(credentials: Credentials) -> str:
    """
    Get the authenticated user's email address.
    
    Args:
        credentials: Google OAuth credentials
    
    Returns:
        User's email address
    """
    try:
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        return user_info.get('email', 'Unknown')
    except Exception:
        return 'Unknown'


def fetch_emails_oauth(credentials: Credentials, count: int = 15) -> Tuple[bool, Any]:
    """
    Fetch recent emails using Gmail API.
    
    Args:
        credentials: Google OAuth credentials
        count: Number of emails to fetch
    
    Returns:
        Tuple of (success, list of emails or error message)
    """
    try:
        service = get_gmail_service(credentials)
        
        # Get list of messages
        results = service.users().messages().list(
            userId='me',
            maxResults=count,
            labelIds=['INBOX']
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return True, []
        
        emails = []
        
        for msg in messages:
            # Get full message details
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            # Extract headers
            headers = message.get('payload', {}).get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            from_addr = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown')
            
            # Get snippet as body preview
            snippet = message.get('snippet', '')
            
            # Format date
            try:
                # Take first 25 chars for display
                date_formatted = date_str[:25] if len(date_str) > 25 else date_str
            except:
                date_formatted = 'Unknown'
            
            emails.append({
                'id': msg['id'],
                'subject': subject,
                'from': from_addr,
                'date': date_formatted,
                'body': snippet[:500] + '...' if len(snippet) > 500 else snippet
            })
        
        return True, emails
        
    except HttpError as e:
        return False, f"Gmail API error: {str(e)}"
    except Exception as e:
        return False, f"Error fetching emails: {str(e)}"


def send_email_oauth(
    credentials: Credentials,
    to: str,
    subject: str,
    body: str,
    from_email: str
) -> Tuple[bool, str]:
    """
    Send an email using Gmail API.
    
    Args:
        credentials: Google OAuth credentials
        to: Recipient email address
        subject: Email subject
        body: Email body
        from_email: Sender's email address
    
    Returns:
        Tuple of (success, message)
    """
    try:
        service = get_gmail_service(credentials)
        
        # Create message
        message = MIMEMultipart()
        message['to'] = to
        message['from'] = from_email
        message['subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send message
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return True, "Email sent successfully!"
        
    except HttpError as e:
        return False, f"Gmail API error: {str(e)}"
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"


def credentials_to_dict(credentials: Credentials) -> Dict:
    """Convert credentials to a dictionary for session storage."""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': list(credentials.scopes) if credentials.scopes else []
    }


def credentials_from_dict(creds_dict: Dict) -> Credentials:
    """Recreate credentials from a dictionary."""
    return Credentials(
        token=creds_dict['token'],
        refresh_token=creds_dict.get('refresh_token'),
        token_uri=creds_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=creds_dict.get('client_id'),
        client_secret=creds_dict.get('client_secret'),
        scopes=creds_dict.get('scopes')
    )
