import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import random
import string
import argparse

# Load environment variables
load_dotenv()

# Email configuration
SMTP_SERVER = os.getenv("EMAIL_HOST", "smtp.elasticemail.com")
SMTP_PORT = int(os.getenv("EMAIL_PORT", "2525"))
SMTP_USERNAME = os.getenv("EMAIL_USER")
SMTP_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Use the authenticated username as sender (this is what Elastic Email allows)
SENDER_EMAIL = SMTP_USERNAME

def generate_otp(length=6):
    """Generate a random OTP of specified length"""
    return ''.join(random.choices(string.digits, k=length))

def send_email(to_email, subject, body):
    """
    Send an email using SMTP configuration
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body (HTML)
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD]):
        print("Email configuration is incomplete")
        return False
    
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = SENDER_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        
        # Add body to email
        message.attach(MIMEText(body, "html"))
        
        # Convert the message to a string
        msg = message.as_string()
        
        # Connect to SMTP server and send email
        print(f"Connecting to {SMTP_SERVER}:{SMTP_PORT}...")
        smtp = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        smtp.set_debuglevel(1)  # Enable verbose logging
        smtp.ehlo()
        smtp.starttls()
        
        print(f"Logging in as {SMTP_USERNAME}...")
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        print(f"Sending email from {SENDER_EMAIL} to {to_email}...")
        smtp.sendmail(SENDER_EMAIL, to_email, msg)
        smtp.quit()
        
        print(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"Failed to send email: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

def send_verification_email(to_email, otp):
    """
    Send a verification email with OTP
    
    Args:
        to_email: Recipient email address
        otp: One-time password for verification
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = "Verify Your Email Address"
    body = f"""
    <html>
    <body>
        <h2>Email Verification</h2>
        <p>Thank you for signing up! Please use the following verification code to complete your registration:</p>
        <h1 style="font-size: 24px; background-color: #f0f0f0; padding: 10px; text-align: center;">{otp}</h1>
        <p>This code will expire in 10 minutes.</p>
        <p>If you didn't request this verification, please ignore this email.</p>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, body)

def main():
    """CLI interface for testing email functionality"""
    parser = argparse.ArgumentParser(description='Send test emails via command line')
    parser.add_argument('--to', required=True, help='Recipient email address')
    parser.add_argument('--subject', default='Test Email', help='Email subject')
    parser.add_argument('--body', default='This is a test email sent from the CLI.', help='Email body')
    parser.add_argument('--verify', action='store_true', help='Send a verification email with OTP instead')
    
    args = parser.parse_args()
    
    if args.verify:
        otp = generate_otp()
        print(f"Generated OTP: {otp}")
        success = send_verification_email(args.to, otp)
    else:
        success = send_email(args.to, args.subject, args.body)
    
    if success:
        print("Email sent successfully!")
    else:
        print("Failed to send email.")

if __name__ == "__main__":
    main() 