#!/usr/bin/env python3

import hashlib
import logging
import os

import boto
import boto.s3.connection
import boto.s3.key
import flask
from flask import request
from html.parser import HTMLParser
import json

import cleanup_svg

import boto_secrets

app = flask.Flask(__name__)
app.logger.setLevel(logging.INFO)
root = os.path.realpath(os.path.dirname(__file__))


@app.route('/', methods=['GET'])
def editor():
    return flask.render_template('editor.html')


@app.route('/svg', methods=['POST'])
def svg():
    """The external endpoint accessed to render a graphie

    Returns a web+graphie link as the response.
    """
    # We're having to disable max_form_memory_size in order to be able to
    # parse the largest of Graphies in our template bank submitted in the body.
    # But we also need to ensure that the request itself is not too large so as
    # to represent a security issue.
    if request.content_length > 3000000:
        return "Request entity too large", 413
    # https://flask.palletsprojects.com/en/stable/web-security/#resource-use
    # https://flask.palletsprojects.com/en/stable/config/#MAX_FORM_MEMORY_SIZE
    request.max_form_memory_size = None

    js = request.form['js']
    svg = request.form['svg']
    raw_other_data = request.form['other_data']

    # Sanitize raw_other_data
    sanitized_other_data = sanitize_input(raw_other_data)

    # Validate sanitized_other_data as JSON
    json_data = json.loads(sanitized_other_data)

    hash = hashlib.sha1(js.encode('utf-8')).hexdigest()
    _maybe_upload_to_s3('%s.js' % hash, js, 'application/javascript')
    _maybe_upload_to_s3('%s-data.json' % hash,
                        _jsonp_wrap(json.dumps(json_data), 'svgData%s' % hash),
                        'application/json')
    svg_url = _maybe_upload_to_s3('%s.svg' % hash, cleanup_svg.cleanup_svg(svg),
                                  'image/svg+xml')

    return (svg_url.
            replace("https://", "web+graphie://").
            replace(".svg", "").
            replace(":443", ""))

class Sanitizer(HTMLParser):
    """Custom HTML parser to remove <script>, <iframe>, and <object> tags."""
    def __init__(self):
        super().__init__()
        self.cleaned_data = []
        # skip indicates whether we're inside a dangerous tag
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "iframe", "object"}:
            # Skip content inside these tags
            self.skip = True
        else:
            # Reconstruct safe opening tags
            self.cleaned_data.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if tag in {"script", "iframe", "object"}:
            # End skipping when the dangerous tag closes
            self.skip = False
        else:
            # Reconstruct safe closing tags
            self.cleaned_data.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            # Add content outside dangerous tags
            self.cleaned_data.append(data)

    def get_cleaned_data(self):
        # Return the reconstructed HTML
        return "".join(self.cleaned_data)

def sanitize_input(input_data):
    """Sanitize input by removing <script>, <iframe>, and <object> tags."""
    parser = Sanitizer()
    # Feed the raw HTML into the parser
    parser.feed(input_data)
    return parser.get_cleaned_data()

def _jsonp_wrap(data, func_name):
    return '%s(%s);' % (func_name, data)


def _maybe_upload_to_s3(key, data, mimetype):
    conn = boto.s3.connection.S3Connection(
            boto_secrets.aws_access_key_id,
            boto_secrets.aws_secret_access_key,
        )
    bucket = conn.get_bucket(boto_secrets.aws_s3_bucket, validate=False)

    k = boto.s3.key.Key(bucket)
    k.key = key
    if k.exists():
        app.logger.info('File already exists, skipping upload: %s' % key)
    else:
        k.set_contents_from_string(
                data,
                headers={'Content-Type': mimetype},
                policy='public-read',
            )

    return k.generate_url(expires_in=0, query_auth=False)


if __name__ == "__main__":
    app.run(debug=True, port=5001, host='::')
