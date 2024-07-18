import imaplib
import email
from email.header import decode_header
import smtplib
from email.mime.text import MIMEText

# Your email credentials
username = "ronsmith.joys@gmail.com"
app_password = "koeh lrvr texj ezco"

# List of email addresses to filter
email_addresses = ["evelyene@devbaytech.com"]

try:
    # Connect to the Gmail IMAP server
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    print("Connected to IMAP server.")
    
    # Login to your account
    mail.login(username, app_password)
    print("Login successful.")
    
    # Function to process and respond to emails
    def process_emails(folder_name, limit=20):
        # Select the folder
        status, messages = mail.select(folder_name)
        
        if status != "OK":
            print(f"Error selecting the {folder_name} folder: {status}. Exiting.")
            return
        
        # Search for all unread emails
        status, messages = mail.search(None, '(UNSEEN)')
        
        if status != "OK":
            print(f"Error searching for unread emails in {folder_name} folder: {status}. Exiting.")
            return
        
        # Convert messages to a list of email IDs and limit to first 20 emails
        email_ids = messages[0].split()[:limit]
        print(f"Found {len(email_ids)} unread emails in {folder_name} folder.")
        
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
            print(f"Sent response to {to_address}")
        
        # Fetch and respond to each email
        for email_id in email_ids:
            print(f"Processing email ID {email_id.decode()}")
            # Fetch the email by ID
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            
            if status != "OK":
                print(f"Error fetching email ID {email_id}. Skipping.")
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
                    
                    # Extract the sender email address
                    from_address = email.utils.parseaddr(from_)[1]
                    
                    # Check if the email is from one of the specified email addresses
                    if from_address not in email_addresses:
                        print(f"Email from {from_address} is not in the specified list. Skipping.")
                        continue
                    
                    print(f"Email from {from_address} with subject: {subject}")
                    
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
                    
                    if folder_name == "Spam":
                        # Move the email to the inbox and mark as not spam
                        result = mail.copy(email_id, 'INBOX')
                        if result[0] == 'OK':
                            mail.store(email_id, '+FLAGS', '\\Deleted')
                            mail.expunge()
                            print(f"Moved email ID {email_id.decode()} from Spam to Inbox.")
                    
                    # Mark the email as seen
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    print(f"Marked email ID {email_id.decode()} as seen.")
                    
                    # Send a response email
                    send_response(from_address, subject, message_id)
        
        # Close the SMTP connection
        smtp_server.quit()
    
    # Process emails in both Spam and Inbox, limiting to first 20 emails in Inbox
    process_emails("[Gmail]/Spam")
    process_emails("INBOX", limit=20)
    
    # Logout and close the IMAP connection
    mail.logout()
    print("Process completed successfully.")

except Exception as e:
    print(f"An error occurred: {e}")
