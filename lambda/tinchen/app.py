from __future__ import print_function
from bs4 import BeautifulSoup
from requests import get

import email
import zipfile
import os
import gzip
import string
import boto3
import urllib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

print('Loading function')

s3 = boto3.client('s3')
s3r = boto3.resource('s3')
xmlDir = "/tmp/output/"

bucket = os.getenv('SesBucketName')
mailSender = os.getenv('MailSender')
mailRecipient = os.getenv('MailRecipient')



def lambda_handler(event, context):
    print('debug event: {}'.format(event))
    #bucket = event['Records'][0]['s3']['bucket']['name']
    
    key = urllib.parse.unquote_plus(event['Records'][0]['ses']['mail']['messageId'], 'utf8')

    try:
        
        # Use waiter to ensure the file is persisted
        waiter = s3.get_waiter('object_exists')
        waiter.wait(Bucket=bucket, Key=key)

        response = s3r.Object( bucket, key)

        # Read the raw text file into a Email Object
        msg = email.message_from_string(response.get()["Body"].read().decode('utf8'))

        processMail(msg)

        
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist '
            'and your bucket is in the same region as this '
            'function.'.format(key, bucket))
        raise e
    #delete_file(key, bucket)
    
def processMail(msg):
    print('Found {} attachments'.format(len(msg.get_payload())))
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            print('########')
            print('Content Type: {}, Content Disposition: {}'.format(ctype, cdispo))

            # skip any text/plain (txt) attachments
            if ctype == 'text/html':
                link = getLink(part.get_payload(decode=True))
                download(link, '/tmp/speiseplan.pdf')
                print('downloaded!')
                sender_ = mailSender
                recipients_ = [mailRecipient]
                title_ = 'Email title here'
                text_ = 'Speiseplan'
                body_ = """<html><head></head><body><h1>Speiseplan</h1><br>Some text."""
                attachments_ = ['/tmp/speiseplan.pdf']

                response_ = send_mail(sender_, recipients_, title_, text_, body_, attachments_)
                print(response_)
                #print(msgpart.get_payload(decode=True))
                #body = msgpart.get_payload(decode=True)  # decode
                #print(body)
    # not multipart - i.e. plain text, no attachments, keeping fingers crossed
    else:
        body = msg.get_payload(decode=True)

def getLink(html):
    #print(html)
    soup = BeautifulSoup(html, 'html.parser')
    print(soup.select('a'))
    for anchor in soup.select('a'):
        spanText = anchor.get_text(strip=True)
        if (spanText.find('Speiseplan') >= 0 and spanText.endswith('PDF') == True):
            return anchor['href']

def download(url, file_name):
    # open in binary mode
    with open(file_name, "wb") as file:
        # get request
        response = get(url)
        # write to file
        file.write(response.content)

def extract_attachment(attachment):
    # Process filename.zip attachments
    if "gzip" in attachment.get_content_type():
        contentdisp = string.split(attachment.get('Content-Disposition'), '=')
        fname = contentdisp[1].replace('\"', '')
        open('/tmp/' + contentdisp[1], 'wb').write(attachment.get_payload(decode=True))
        # This assumes we have filename.xml.gz, if we get this wrong, we will just
        # ignore the report
        xmlname = fname[:-3]
        open(xmlDir + xmlname, 'wb').write(gzip.open('/tmp/' + contentdisp[1], 'rb').read())

    # Process filename.xml.gz attachments (Providers not complying to standards)
    elif "zip" in attachment.get_content_type():
        open('/tmp/attachment.zip', 'wb').write(attachment.get_payload(decode=True))
        with zipfile.ZipFile('/tmp/attachment.zip', "r") as z:
            z.extractall(xmlDir)

    else:
        print('Skipping ' + attachment.get_content_type())
            
# Delete the file in the current bucket
def delete_file(key, bucket):
    s3.delete_object(Bucket=bucket, Key=key)
    print("%s deleted fom %s ") % (key, bucket)

def create_multipart_message(
        sender: str, recipients: list, title: str, text: str=None, html: str=None, attachments: list=None)\
        -> MIMEMultipart:
    """
    Creates a MIME multipart message object.
    Uses only the Python `email` standard library.
    Emails, both sender and recipients, can be just the email string or have the format 'The Name <the_email@host.com>'.

    :param sender: The sender.
    :param recipients: List of recipients. Needs to be a list, even if only one recipient.
    :param title: The title of the email.
    :param text: The text version of the email body (optional).
    :param html: The html version of the email body (optional).
    :param attachments: List of files to attach in the email.
    :return: A `MIMEMultipart` to be used to send the email.
    """
    multipart_content_subtype = 'alternative' if text and html else 'mixed'
    msg = MIMEMultipart(multipart_content_subtype)
    msg['Subject'] = title
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)

    # Record the MIME types of both parts - text/plain and text/html.
    # According to RFC 2046, the last part of a multipart message, in this case the HTML message, is best and preferred.
    if text:
        part = MIMEText(text, 'plain')
        msg.attach(part)
    if html:
        part = MIMEText(html, 'html')
        msg.attach(part)

    # Add attachments
    for attachment in attachments or []:
        with open(attachment, 'rb') as f:
            part = MIMEApplication(f.read())
            part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment))
            msg.attach(part)

    return msg


def send_mail(
        sender: str, recipients: list, title: str, text: str=None, html: str=None, attachments: list=None) -> dict:
    """
    Send email to recipients. Sends one mail to all recipients.
    The sender needs to be a verified email in SES.
    """
    msg = create_multipart_message(sender, recipients, title, text, html, attachments)
    ses_client = boto3.client('ses')  # Use your settings here
    return ses_client.send_raw_email(
        Source=sender,
        Destinations=recipients,
        RawMessage={'Data': msg.as_string()}
    )

if __name__ == '__main__':
    f = open('lambda/tinchen/email.sample', 'r')
    msg = email.message_from_string(f.read())
    processMail(msg)