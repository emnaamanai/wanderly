from flask import Flask, render_template
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash
import sqlite3
app = Flask(__name__)
import db
db.init_app(app)

@app.route("/")
def accueil():
    return render_template("index.html")
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash

app = Flask(__name__)

import db
db.init_app(app)


@app.route("/")
def accueil():
    return render_template("index.html")


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    if request.method == "POST":
        pseudo = request.form["pseudo"]
        email = request.form["email"]
        mot_de_passe = request.form["mot_de_passe"]

        mot_de_passe_hash = generate_password_hash(mot_de_passe)

        base = db.get_db()
        try:
            base.execute(
                "INSERT INTO utilisateur (pseudo, email, mot_de_passe_hash) VALUES (?, ?, ?)",
                (pseudo, email, mot_de_passe_hash),
            )
            base.commit()
        except sqlite3.IntegrityError:
            erreur = "Ce pseudo ou cet e-mail est déjà utilisé."
            return render_template("inscription.html", erreur=erreur)

        return redirect(url_for("accueil"))

        return redirect(url_for("accueil"))

    return render_template("inscription.html")