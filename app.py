#!/usr/bin/env python3

import hashlib
import logging
import os

import boto
import boto.s3.connection
import boto.s3.key
import flask
from flask import request

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
    if request.content_length > 1500000:
        return "Request entity too large", 413
    # https://flask.palletsprojects.com/en/stable/web-security/#resource-use
    # https://flask.palletsprojects.com/en/stable/config/#MAX_FORM_MEMORY_SIZE
    request.max_form_memory_size = None

    js = request.form['js']
    svg = request.form['svg']
    other_data = request.form['other_data']

    hash = hashlib.sha1(js.encode('utf-8')).hexdigest()
    _maybe_upload_to_s3('%s.js' % hash, js, 'application/javascript')
    _maybe_upload_to_s3('%s-data.json' % hash,
                        _jsonp_wrap(other_data, 'svgData%s' % hash),
                        'application/json')
    svg_url = _maybe_upload_to_s3('%s.svg' % hash, cleanup_svg.cleanup_svg(svg),
                                  'image/svg+xml')

    return (svg_url.
            replace("https://", "web+graphie://").
            replace(".svg", "").
            replace(":443", ""))


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
