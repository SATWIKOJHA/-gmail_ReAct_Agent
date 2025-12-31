"""
Gmail Service Module
Handles IMAP (reading emails) and SMTP (sending emails) operations.
"""

from __future__ import annotations

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime
from typing import Optional, Tuple, List, Union


IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def authenticate(email_address: str, app_password: str) -> Tuple[bool, str]:
    """
    Authenticate user credentials using IMAP.
    
    Args:
        email_address: User's Gmail address
        app_password: User's App Password (16 characters)
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        print(f"[DEBUG] Attempting to connect to {IMAP_SERVER}...")
        imap = imaplib.IMAP4_SSL(IMAP_SERVER)
        print(f"[DEBUG] Connected! Attempting login for: {email_address}")
        imap.login(email_address, app_password)
        print("[DEBUG] Login successful!")
        imap.logout()
        return True, "Authentication successful!"
    except imaplib.IMAP4.error as e:
        error_msg = str(e)
        print(f"[DEBUG] IMAP Error: {error_msg}")
        if "AUTHENTICATIONFAILED" in error_msg.upper() or "Invalid credentials" in error_msg:
            return False, "Authentication failed: Please use an App Password, not your regular Gmail password. See instructions below."
        return False, f"Authentication failed: {error_msg}"
    except Exception as e:
        print(f"[DEBUG] Exception: {type(e).__name__}: {str(e)}")
        return False, f"Connection error: {str(e)}"


def decode_mime_header(header_value: str) -> str:
    """Decode MIME encoded header value."""
    if header_value is None:
        return ""
    
    decoded_parts = []
    for part, encoding in decode_header(header_value):
        if isinstance(part, bytes):
            try:
                decoded_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
            except:
                decoded_parts.append(part.decode('utf-8', errors='replace'))
        else:
            decoded_parts.append(part)
    
    return ''.join(decoded_parts)


def get_email_body(msg) -> str:
    """Extract the body text from an email message."""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='replace')
                        break
                except:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='replace')
        except:
            body = str(msg.get_payload())
    
    return body[:500] + "..." if len(body) > 500 else body


def fetch_emails(email_address: str, app_password: str, count: int = 10) -> Tuple[bool, Union[List, str]]:
    """
    Fetch recent emails from inbox.
    
    Args:
        email_address: User's Gmail address
        app_password: User's App Password
        count: Number of emails to fetch (default: 10)
    
    Returns:
        Tuple of (success: bool, emails: list or error_message: str)
    """
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER)
        imap.login(email_address, app_password)
        imap.select("INBOX")
        
        # Search for all emails
        status, messages = imap.search(None, "ALL")
        
        if status != "OK":
            return False, "Failed to fetch emails"
        
        email_ids = messages[0].split()
        
        # Get the latest emails
        email_ids = email_ids[-count:] if len(email_ids) > count else email_ids
        email_ids = email_ids[::-1]  # Reverse to show newest first
        
        emails = []
        
        for email_id in email_ids:
            status, msg_data = imap.fetch(email_id, "(RFC822)")
            
            if status != "OK":
                continue
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Extract email details
                    subject = decode_mime_header(msg.get("Subject", "No Subject"))
                    from_addr = decode_mime_header(msg.get("From", "Unknown"))
                    date_str = msg.get("Date", "")
                    body = get_email_body(msg)
                    
                    # Parse date
                    try:
                        date_parsed = email.utils.parsedate_to_datetime(date_str)
                        date_formatted = date_parsed.strftime("%b %d, %Y %I:%M %p")
                    except:
                        date_formatted = date_str[:20] if date_str else "Unknown"
                    
                    emails.append({
                        "id": email_id.decode(),
                        "subject": subject,
                        "from": from_addr,
                        "date": date_formatted,
                        "body": body
                    })
        
        imap.logout()
        return True, emails
        
    except imaplib.IMAP4.error as e:
        return False, f"IMAP error: {str(e)}"
    except Exception as e:
        return False, f"Error fetching emails: {str(e)}"


def send_email(
    email_address: str, 
    app_password: str, 
    to: str, 
    subject: str, 
    body: str
) -> Tuple[bool, str]:
    """
    Send an email via SMTP.
    
    Args:
        email_address: Sender's Gmail address
        app_password: Sender's App Password
        to: Recipient email address
        subject: Email subject
        body: Email body text
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = email_address
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        # Connect and send
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(email_address, app_password)
        server.send_message(msg)
        server.quit()
        
        return True, "Email sent successfully!"
        
    except smtplib.SMTPAuthenticationError:
        return False, "Authentication failed: Invalid credentials"
    except smtplib.SMTPRecipientsRefused:
        return False, "Failed: Invalid recipient email address"
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"
