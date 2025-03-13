#!/usr/bin/env python3

import hashlib
import logging
import os

import boto
import boto.s3.connection
import boto.s3.key
import flask
from flask import request
import esprima

import cleanup_svg

import boto_secrets

app = flask.Flask(__name__)
app.logger.setLevel(logging.INFO)
root = os.path.realpath(os.path.dirname(__file__))


@app.route('/', methods=['GET'])
def editor():
    return flask.render_template('editor.html')

def contains_forbidden_js(js_code):
    """
    Parses JavaScript code and checks for:
    - Function calls to eval(), alert(), require(), Function()
    - References to document in expressions
    """
    forbidden_calls = {"eval", "alert", "require", "Function"}
    forbidden_identifiers = {"document"}

    try:
        # Parse JavaScript into AST and convert to dictionary
        tree = esprima.parseScript(js_code, tolerant=True).toDict()
        
        stack = [tree]

        while stack:
            node = stack.pop()

            if not isinstance(node, dict) or 'type' not in node:
                continue

            # Check for function calls like eval(), alert(), require(), Function()
            if node["type"] == "CallExpression" and "callee" in node:
                callee = node["callee"]
                if callee.get("type") == "Identifier" and callee.get("name") in forbidden_calls:
                    return f"Error: Forbidden function '{callee['name']}' used", 400

            # Check for usage of 'document' (e.g., document.getElementById())
            if node["type"] == "MemberExpression" and "object" in node:
                obj = node["object"]
                if obj.get("type") == "Identifier" and obj.get("name") in forbidden_identifiers:
                    return f"Error: Forbidden identifier '{obj['name']}' used", 400

            # Add child nodes to the stack for further inspection
            for key, value in node.items():
                if isinstance(value, dict):  # If it's a nested object, add it to the stack
                    stack.append(value)
                elif isinstance(value, list):  # If it's a list of nodes, add all to the stack
                    stack.extend([child for child in value if isinstance(child, dict)])

        return None

    except Exception as e:
        return f"Error parsing JavaScript: {str(e)}", 400

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
    other_data = request.form['other_data']

    # Check JavaScript security using AST
    js_error = contains_forbidden_js(js)
    if js_error:
        return js_error

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
