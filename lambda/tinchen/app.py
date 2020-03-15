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

print('Loading function')

s3 = boto3.client('s3')
s3r = boto3.resource('s3')
xmlDir = "/tmp/output/"




def lambda_handler(event, context):
    print('debug event: {}'.format(event))
    #bucket = event['Records'][0]['s3']['bucket']['name']
    bucket = USER = os.getenv('SesBucketName')
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
                #print(msgpart.get_payload(decode=True))
                #body = msgpart.get_payload(decode=True)  # decode
                #print(body)
    # not multipart - i.e. plain text, no attachments, keeping fingers crossed
    else:
        body = msg.get_payload(decode=True)

def getLink(html):
    soup = BeautifulSoup(html, 'html.parser')
    print(soup.select('a > span'))
    for anchor in soup.select('a > span'):
        spanText = anchor.get_text(strip=True)
        if (spanText.find('Speiseplan') >= 0 and spanText.endswith('pdf') == True):
            return anchor.find_parent()['href']

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


if __name__ == '__main__':
    f = open('lambda/tinchen/email.sample', 'r')
    msg = email.message_from_string(f.read())
    processMail(msg)