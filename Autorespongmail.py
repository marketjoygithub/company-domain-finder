import imaplib
import email
from email.header import decode_header
import smtplib
from email.mime.text import MIMEText

# Your email credentials
username = "ronsmith.joys@gmail.com"
app_password = "koeh lrvr texj ezco"


try:
    # Connect to the Gmail IMAP server
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    print("Connected to IMAP server.")
    
    # Login to your account
    mail.login(username, app_password)
    print("Login successful.")
    
    # Select the spam folder
    status, messages = mail.select('[Gmail]/Spam')
    
    if status != "OK":
        print(f"Error selecting the Spam folder: {status}. Exiting.")
        mail.logout()
        exit()
    else:
        print("Spam folder selected.")
    
    # Search for all unread emails
    status, messages = mail.search(None, '(UNSEEN)')
    
    if status != "OK":
        print(f"Error searching for unread emails: {status}. Exiting.")
        mail.logout()
        exit()
    else:
        print("Unread emails found.")
    
    # Convert messages to a list of email IDs
    email_ids = messages[0].split()
    
    # Determine how many emails to respond to (up to 5 or less if fewer unread emails)
    num_emails_to_respond = min(5, len(email_ids))
    print(f"Responding to {num_emails_to_respond} emails.")
    
    # Create an SMTP connection to send the response email
    smtp_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    smtp_server.login(username, app_password)
    print("SMTP login successful.")
    
    # Function to send a response email
    def send_response(to_address, subject, message_id):
        msg = MIMEText("Yes, I received your mail")
        msg["Subject"] = f"Re: {subject}"
        msg["From"] = username
        msg["To"] = to_address
        msg["In-Reply-To"] = message_id
        msg["References"] = message_id
        smtp_server.sendmail(username, to_address, msg.as_string())
    
    # Fetch and respond to each email
    for i in range(num_emails_to_respond):
        # Fetch the email by ID
        status, msg_data = mail.fetch(email_ids[i], "(RFC822)")
        
        if status != "OK":
            print(f"Error fetching email ID {email_ids[i]}. Skipping.")
            continue
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                # Parse the email
                msg = email.message_from_bytes(response_part[1])
                
                # Decode the email subject
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    # If it's a bytes type, decode to string
                    subject = subject.decode(encoding if encoding else "utf-8")
                
                # Decode the email from
                from_ = msg.get("From")
                
                print("Subject:", subject)
                print("From:", from_)
                
                # Extract the sender email address
                from_address = email.utils.parseaddr(from_)[1]
                
                # Extract the message ID
                message_id = msg["Message-ID"]
                
                # If the email message is multipart
                if msg.is_multipart():
                    # Iterate over email parts
                    for part in msg.walk():
                        # Extract content type of email
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        
                        try:
                            # Get the email body
                            body = part.get_payload(decode=True).decode()
                            print("Body:", body)
                        except:
                            pass
                else:
                    # Extract content type of email
                    content_type = msg.get_content_type()
                    
                    # Get the email body
                    body = msg.get_payload(decode=True).decode()
                    print("Body:", body)
                
                print("="*50)
                
                # Move the email to the inbox and mark as not spam
                mail.store(email_ids[i], '-X-GM-LABELS', '\\Spam')
                mail.store(email_ids[i], '+X-GM-LABELS', '\\Inbox')
                mail.store(email_ids[i], '+FLAGS', '\\Seen')
                
                # Send a response email
                send_response(from_address, subject, message_id)
    
    # Logout and close the connections
    mail.logout()
    smtp_server.quit()
    print("Process completed successfully.")

except Exception as e:
    print(f"An error occurred: {e}")
