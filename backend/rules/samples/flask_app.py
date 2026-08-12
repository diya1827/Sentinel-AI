# Test cases for the Flask XSS rules.

import flask
from flask import Flask, request, make_response, render_template_string
from flask import render_template
import markupsafe
from markupsafe import Markup, escape

app = Flask(__name__)


@app.route("/hello")
def hello():
    name = request.args.get("name")
    # ruleid: flask-render-template-string-tainted
    return render_template_string("<h1>Hello " + name + "</h1>")


@app.route("/echo")
def echo():
    term = request.args.get("term")
    # ruleid: flask-reflected-response-tainted
    return make_response("<p>You searched for: " + term + "</p>")


@app.route("/comment")
def comment():
    body = request.form.get("body")
    # ruleid: python-markup-marks-tainted-safe
    return Markup(body)


@app.route("/safe-template")
def safe_template():
    name = request.args.get("name")
    # ok: flask-render-template-string-tainted
    return render_template("hello.html", name=name)


@app.route("/safe-escaped")
def safe_escaped():
    term = request.args.get("term")
    # ok: flask-reflected-response-tainted
    return make_response(escape(term))
