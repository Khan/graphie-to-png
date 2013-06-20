import hashlib
import os
import shutil
import subprocess
import tempfile

import boto
import boto.s3.connection
import flask
from flask import request
import werkzeug.contrib.cache

import secrets

app = flask.Flask(__name__)
root = os.path.realpath(os.path.dirname(__file__))
cache = werkzeug.contrib.cache.SimpleCache()


@app.route('/', methods=['GET'])
def hello():
    return flask.render_template('hello.html')


@app.route('/png', methods=['POST'])
def png():
    js = request.form['js']
    js += "\nforceLabelTypeset();\n"
    png = _js_to_png(js)

    # TODO(alpert): If graphie changes and gives a new png this just overwrites
    hash = hashlib.sha1(js).hexdigest()
    _put_to_s3('%s.js' % hash, js, 'application/javascript')
    url = _put_to_s3('%s.png' % hash, png, 'image/png')

    if request.args.get("url_only"):
        return url
    else:
        return flask.redirect(url)


def _js_to_png(js):
    key = os.urandom(8).encode('hex')
    html_path = os.path.join(root, 'plain_graph_%s.html' % key)
    with open(html_path, 'w') as f:
        f.write(flask.render_template('plain_graph.html', js=js))

    png_dir = tempfile.mkdtemp()

    try:
        subprocess.check_call([
                os.path.join(root, 'webkit2png', 'webkit2png'),
                '--fullsize',
                '--selector=.graphie',
                '--width=20',
                '--height=20',
                '--clipwidth=20',
                '--clipheight=20',
                '--zoom=1.0',
                '--transparent',
                '--dir=%s' % png_dir,
                '--filename=image',  # giving image-full.png
                html_path,
            ])

        with open(os.path.join(png_dir, 'image-full.png')) as f:
            return f.read()
    finally:
        os.unlink(html_path)
        shutil.rmtree(png_dir)


def _put_to_s3(key, data, mimetype):
    conn = boto.s3.connection.S3Connection(
            secrets.aws_access_key_id,
            secrets.aws_secret_access_key,
        )
    bucket = conn.get_bucket(secrets.aws_s3_bucket)

    k = boto.s3.key.Key(bucket)
    k.key = key
    k.set_contents_from_string(
            data,
            headers={'Content-Type': mimetype},
            policy='public-read',
        )

    return k.generate_url(expires_in=0, query_auth=False)


if __name__ == "__main__":
    app.run(debug=True)
