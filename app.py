from flask import Flask, request
from flask.templating import render_template
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def hello():
    person = {"name": "Seth", "age": "30"}
    return render_template("steward-card.html", person=person)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)