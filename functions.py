from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json


# takes in any parameter and prints it with the current time
def print_with_time(text):
    text = str(text)
    current_time = datetime.now().strftime("%D %H:%M:%S")
    print(text + " (" + current_time + ")")


# sends an email with the subject and message passed, in order for this function to work,
# the info.json file must be in the current working directory
def send_email(html, subject, receiver):
    with open("info.json", "r", encoding="utf-8") as f:
        info = json.load(f)

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = f'Movie-Notifier.com <{info["email"]["username"]}>'
    msg['To'] = receiver

    body = MIMEText(html, 'html', "utf-8")
    msg.attach(body)

    server = smtplib.SMTP_SSL(info["email"]["host"], info["email"]["port"])
    server.ehlo()
    server.login(info["email"]["username"], info["email"]["password"])
    server.send_message(msg)
    print_with_time(f"Mail sent to {receiver}...")
    server.quit()
