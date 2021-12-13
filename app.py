from flask import Flask, request
from flask.templating import render_template
app = Flask(__name__, static_folder="assets")

@app.route("/", methods=["GET", "POST"])
def main():
    return render_template("index.html")