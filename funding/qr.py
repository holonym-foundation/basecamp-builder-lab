#!/usr/bin/env python3
"""Generate the participant QR locally after the operator creates the Google Form."""
import argparse
from urllib.parse import urlparse
import qrcode

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', required=True)
parser.add_argument('--out', required=True)
args = parser.parse_args()
url = urlparse(args.url)
if url.scheme != 'https' or url.hostname not in {'docs.google.com', 'forms.gle'} or url.username or url.fragment:
    parser.error('Use the HTTPS participant Google Forms URL')
if url.hostname == 'docs.google.com' and not (url.path.startswith('/forms/') and url.path.endswith('/viewform')):
    parser.error('Use the published viewform URL, not the edit URL')
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=4)
qr.add_data(args.url)
qr.make(fit=True)
qr.make_image(fill_color='black', back_color='white').save(args.out)
print(args.out)
