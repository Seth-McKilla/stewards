from flask import Flask, request
from flask.templating import render_template
app = Flask(__name__, static_folder="assets")

@app.route("/", methods=["GET", "POST"])


def main():
    # Insert API logic here
    stewards = []
    return render_template("index.html", stewards=stewards)