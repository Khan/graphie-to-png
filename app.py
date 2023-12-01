#!/usr/bin/env python
# TODO(colin): fix these lint errors (http://pep8.readthedocs.io/en/release-1.7.x/intro.html#error-codes)
# pep8-disable:E128

import hashlib
import json
import os
import re
import signal
import subprocess
import threading

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


class RenderTimeout(Exception):
    pass


@app.errorhandler(RenderTimeout)
def handle_timeout_error(error):
    return 'Rendering took too long, try again.', 500


@app.route('/', methods=['GET'])
def editor():
    return flask.render_template('editor.html')


@app.route('/svg', methods=['POST'])
def svg():
    """The external endpoint accessed to render a graphie

    Returns a web+graphie link as the response.
    """
    js = request.form['js']

    svg, other_data = _js_to_svg(js)

    hash = hashlib.sha1(js.encode('utf-8')).hexdigest()
    _put_to_s3('%s.js' % hash, js, 'application/javascript')
    _put_to_s3('%s-data.json' % hash,
               _jsonp_wrap(other_data, 'svgData%s' % hash), 'application/json')
    svg_url = _put_to_s3('%s.svg' % hash, cleanup_svg.cleanup_svg(svg),
                     'image/svg+xml')

    match = URL_REGEX.match(svg_url)

    return 'web+graphie://%s/%s' % match.groups()


@app.route('/svgize', methods=['POST'])
def svgize():
    """The rendering endpoint accessed by phantomjs"""
    js = request.form['js']
    return flask.render_template('plain_graph.html', js=js)


def run_with_timeout(command, timeout):
    """Run a command as a subprocess with a specified timeout in seconds

    If the subprocess successfully exits, this returns a string of output from
    the command. Otherwise, this returns `None`.
    """
    # An object of data that can be accessed inside the thread
    data = {}
    data['process'] = None
    data['stdout'] = None

    # The function to be run in a separate thread
    def thread_runner():
        data['process'] = subprocess.Popen(command, stdout=subprocess.PIPE,
                                           preexec_fn=os.setpgrp)
        data['stdout'] = data['process'].communicate()[0]

    thread = threading.Thread(target=thread_runner)
    thread.start()

    thread.join(timeout)
    if thread.is_alive():
        # If the thread is still running, kill it and ignore the output
        # os.killpg taken from http://stackoverflow.com/a/4791612/57318
        os.killpg(data['process'].pid, signal.SIGKILL)
        thread.join()
        return None
    else:
        return data['stdout']


def _js_to_svg(js):
    # subprocess.Popen() can't handle unicode, and phantomjs will produce
    # mangled results if we use js.encode('utf-8'). Note that JS allows
    # \u escapes in identifiers as well as in strings, so this approach
    # should work no matter where the non-ASCII characters are located.
    if isinstance(js, unicode):
        js = "".join([
            "\\u{0:04X}".format(ord(c)) if ord(c) > 127 else str(c)
            for c in js
        ])
    # Run phantomjs with a 55 second timeout. Gunicorn kills its child threads
    # after 60 seconds, so we need to kill the phantomjs thread before then.
    # TODO(csilvers): just use /usr/bin/timeout instead.
    json_data = run_with_timeout([
        os.path.join(root, 'node_modules', '.bin', 'phantomjs'),
        os.path.join(root, 'phantom_svg.js'),
        js
    ], 55)

    if json_data is None:
        raise RenderTimeout()

    data = {}
    try:
        data = json.loads(json_data)
    except:
        print("Failed to parse JSON: " + json_data)
        raise RenderTimeout()

    return data['svg'], data['other_data']


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
