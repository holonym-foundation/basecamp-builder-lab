#!/usr/bin/env python3
"""Generate a participant QR locally for the hosted workshop or optional Google Form."""
import argparse
from urllib.parse import urlparse
import qrcode
import qrcode.image.svg

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', required=True)
parser.add_argument('--out', required=True)
args = parser.parse_args()
url = urlparse(args.url)
workshop_host = 'sui-basecamp-funding.j94fv2pvjn.chatgpt.site'
if url.scheme != 'https' or url.hostname not in {'docs.google.com', 'forms.gle', workshop_host} or url.username or url.fragment or url.port:
    parser.error('Use the HTTPS workshop registration or participant Google Forms URL')
if url.hostname == workshop_host and (url.path not in {'', '/'} or url.query):
    parser.error('Use the participant workshop root URL, never operator or rehearsal links')
if url.hostname == 'docs.google.com' and not (url.path.startswith('/forms/') and url.path.endswith('/viewform')):
    parser.error('Use the published viewform URL, not the edit URL')
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=4)
qr.add_data(args.url)
qr.make(fit=True)
if args.out.lower().endswith('.svg'):
    qr.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(args.out)
else:
    qr.make_image(fill_color='black', back_color='white').save(args.out)
print(args.out)
