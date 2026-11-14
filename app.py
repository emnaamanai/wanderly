import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, g,abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "wanderly-cle-secrete-a-changer-123"

import db
db.init_app(app)
def login_required(vue):
    @wraps(vue)
    def vue_protegee(**kwargs):
        if g.utilisateur is None:
            return redirect(url_for("connexion"))
        return vue(**kwargs)
    return vue_protegee
def admin_required(vue):
    @wraps(vue)
    def vue_protegee(**kwargs):
        if g.utilisateur is None:
            return redirect(url_for("connexion"))
        if g.utilisateur["role"] != "admin":
            abort(403)
        return vue(**kwargs)
    return vue_protegee
@app.route("/")
def accueil():
    lieux = db.get_db().execute(
        "SELECT lieu.*, categorie.nom AS categorie "
        "FROM lieu JOIN categorie ON lieu.categorie_id = categorie.id "
        "ORDER BY lieu.id DESC"
    ).fetchall()
    return render_template("index.html", lieux=lieux)


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    if request.method == "POST":
        pseudo = request.form["pseudo"]
        email = request.form["email"]
        mot_de_passe = request.form["mot_de_passe"]

        mot_de_passe_hash = generate_password_hash(mot_de_passe)

        base = db.get_db()
        try:
            curseur = base.execute(
                "INSERT INTO utilisateur (pseudo, email, mot_de_passe_hash) VALUES (?, ?, ?)",
                (pseudo, email, mot_de_passe_hash),
            )
            base.commit()
        except sqlite3.IntegrityError:
            erreur = "Ce pseudo ou cet e-mail est déjà utilisé."
            return render_template("inscription.html", erreur=erreur)

        session.clear()
        session["utilisateur_id"] = curseur.lastrowid
        return redirect(url_for("accueil"))

    return render_template("inscription.html")
@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    if request.method == "POST":
        pseudo = request.form["pseudo"]
        mot_de_passe = request.form["mot_de_passe"]

        base = db.get_db()
        utilisateur = base.execute(
            "SELECT * FROM utilisateur WHERE pseudo = ?", (pseudo,)
        ).fetchone()

        if utilisateur is None or not check_password_hash(
            utilisateur["mot_de_passe_hash"], mot_de_passe
        ):
            return render_template(
                "connexion.html", erreur="Pseudo ou mot de passe incorrect."
            )

        session.clear()
        session["utilisateur_id"] = utilisateur["id"]
        return redirect(url_for("accueil"))

    return render_template("connexion.html")
@app.before_request
def charger_utilisateur():
    utilisateur_id = session.get("utilisateur_id")
    if utilisateur_id is None:
        g.utilisateur = None
    else:
        g.utilisateur = db.get_db().execute(
            "SELECT * FROM utilisateur WHERE id = ?", (utilisateur_id,)
        ).fetchone()


@app.route("/deconnexion")
def deconnexion():
    session.clear()
    return redirect(url_for("accueil"))
@app.route("/profil")
@login_required
def profil():
    return render_template("profil.html")
@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html")