#!/usr/bin/env python
# TODO(colin): fix these lint errors (http://pep8.readthedocs.io/en/release-1.7.x/intro.html#error-codes)
# pep8-disable:E128

import hashlib
import os
import re
import json

import third_party.boto
import third_party.boto.s3.connection
import third_party.boto.s3.key
import flask
from flask import request
import werkzeug.contrib.cache

import cleanup_svg

import secrets

app = flask.Flask(__name__)
root = os.path.realpath(os.path.dirname(__file__))
cache = werkzeug.contrib.cache.SimpleCache()


URL_REGEX = re.compile(
    r'https://([^/]+)/([a-f0-9]{40})\.svg')


@app.route('/', methods=['GET'])
def editor():
    return flask.render_template('editor.html')


@app.route('/svg', methods=['POST'])
def svg():
    """The external endpoint accessed to render a graphie

    Returns a web+graphie link as the response.
    """
    js = request.form['js']
    svg = request.form['svg']
    other_data = json.loads(request.form['other_data'])

    hash = hashlib.sha1(js.encode('utf-8')).hexdigest()
    _put_to_s3('%s.js' % hash, js, 'application/javascript')
    _put_to_s3('%s-data.json' % hash,
               _jsonp_wrap(other_data, 'svgData%s' % hash), 'application/json')
    svg_url = _put_to_s3('%s.svg' % hash, cleanup_svg.cleanup_svg(svg),
                     'image/svg+xml')

    match = URL_REGEX.match(svg_url)

    return 'web+graphie://%s/%s' % match.groups()


def _jsonp_wrap(data, func_name):
    return '%s(%s);' % (func_name, data)


def _put_to_s3(key, data, mimetype):
    conn = third_party.boto.s3.connection.S3Connection(
            secrets.aws_access_key_id,
            secrets.aws_secret_access_key,
        )
    bucket = conn.get_bucket(secrets.aws_s3_bucket, validate=False)

    k = third_party.boto.s3.key.Key(bucket)
    k.key = key
    k.set_contents_from_string(
            data,
            headers={'Content-Type': mimetype},
            policy='public-read',
        )

    return k.generate_url(expires_in=0, query_auth=False)


if __name__ == "__main__":
    app.run(debug=True, port=5001, host='::')
