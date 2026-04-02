import os
import smtplib
from email.message import EmailMessage

def send_report_email(markdown_path: str):
    """Reads the generated markdown report and emails it to the recipient."""
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    recipient = os.getenv("RECIPIENT_EMAIL", smtp_email) # Default recipient to self
    
    if not smtp_email or not smtp_password:
        return
        
    try:
        with open(markdown_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        msg = EmailMessage()
        msg.set_content(content)
        msg["Subject"] = "🚀 AI Job Search Agent - Daily Curated Report"
        msg["From"] = smtp_email
        msg["To"] = recipient

        # Using standard Gmail SMTP settings. Use an App Password!
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_email, smtp_password)
        server.send_message(msg)
        server.quit()
        
        print(f"Successfully emailed the curated report to {recipient}!")
    except Exception as e:
        print(f"Failed to send email: {e}")
