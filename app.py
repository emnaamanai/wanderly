from flask import Flask, render_template

app = Flask(__name__)
import db
db.init_app(app)

@app.route("/")
def accueil():
    return render_template("index.html")