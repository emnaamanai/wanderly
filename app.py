import sqlite3
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, session, g, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "wanderly-cle-secrete-a-changer-123"

import db
db.init_app(app)


GOUVERNORATS = [
    "Ariana", "Béja", "Ben Arous", "Bizerte", "Gabès", "Gafsa", "Jendouba",
    "Kairouan", "Kasserine", "Kébili", "Le Kef", "Mahdia", "La Manouba",
    "Médenine", "Monastir", "Nabeul", "Sfax", "Sidi Bouzid", "Siliana",
    "Sousse", "Tataouine", "Tozeur", "Tunis", "Zaghouan",
]
LIEUX_PAR_PAGE = 3

def en_nombre(texte):
    try:
        return float(texte)
    except ValueError:
        return None


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


@app.before_request
def charger_utilisateur():
    utilisateur_id = session.get("utilisateur_id")
    if utilisateur_id is None:
        g.utilisateur = None
    else:
        g.utilisateur = db.get_db().execute(
            "SELECT * FROM utilisateur WHERE id = ?", (utilisateur_id,)
        ).fetchone()


@app.route("/")
def accueil():
    base = db.get_db()

    categorie_id = request.args.get("categorie", "")
    region = request.args.get("region", "")
    prix_min = request.args.get("prix_min", "")
    prix_max = request.args.get("prix_max", "")
    page = request.args.get("page", 1, type=int)

    depuis = (
        "FROM lieu JOIN categorie ON lieu.categorie_id = categorie.id "
        "WHERE 1 = 1"
    )
    parametres = []

    if categorie_id:
        depuis += " AND lieu.categorie_id = ?"
        parametres.append(categorie_id)
    if region:
        depuis += " AND lieu.region = ?"
        parametres.append(region)

    minimum = en_nombre(prix_min)
    if minimum is not None:
        depuis += " AND lieu.prix >= ?"
        parametres.append(minimum)
    maximum = en_nombre(prix_max)
    if maximum is not None:
        depuis += " AND lieu.prix <= ?"
        parametres.append(maximum)

    total = base.execute("SELECT COUNT(*) " + depuis, parametres).fetchone()[0]
    nb_pages = max(1, (total + LIEUX_PAR_PAGE - 1) // LIEUX_PAR_PAGE)
    page = min(max(page, 1), nb_pages)

    lieux = base.execute(
        "SELECT lieu.*, categorie.nom AS categorie " + depuis +
        " ORDER BY lieu.id DESC LIMIT ? OFFSET ?",
        parametres + [LIEUX_PAR_PAGE, (page - 1) * LIEUX_PAR_PAGE],
    ).fetchall()

    categories = base.execute("SELECT * FROM categorie ORDER BY nom").fetchall()
    prix_le_plus_haut = base.execute("SELECT MAX(prix) FROM lieu").fetchone()[0] or 0

    filtres = {
        "categorie": categorie_id,
        "region": region,
        "prix_min": prix_min,
        "prix_max": prix_max,
    }

    return render_template(
        "index.html",
        lieux=lieux,
        categories=categories,
        gouvernorats=GOUVERNORATS,
        categorie_id=categorie_id,
        region=region,
        prix_min=prix_min,
        prix_max=prix_max,
        prix_le_plus_haut=prix_le_plus_haut,
        page=page,
        nb_pages=nb_pages,
        filtres=filtres,
    )

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
@app.route("/lieux/ajouter", methods=["GET", "POST"])
@login_required
def ajouter_lieu():
    base = db.get_db()
    categories = base.execute("SELECT * FROM categorie ORDER BY nom").fetchall()

    if request.method == "POST":
        nom = request.form["nom"].strip()
        categorie_id = request.form["categorie"]
        region = request.form["region"]
        description = request.form["description"].strip()
        infos_pratiques = request.form["infos_pratiques"].strip()
        prix = en_nombre(request.form["prix"])
        latitude = en_nombre(request.form["latitude"])
        longitude = en_nombre(request.form["longitude"])

        if (not nom or region not in GOUVERNORATS or prix is None or prix < 0
                or latitude is None or longitude is None):
            return render_template(
                "ajouter_lieu.html",
                erreur="Merci de remplir correctement tous les champs obligatoires.",
                categories=categories,
                gouvernorats=GOUVERNORATS,
            )

        base.execute(
            "INSERT INTO lieu (nom, description, region, prix, latitude, longitude, "
            "infos_pratiques, auteur_id, categorie_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (nom, description, region, prix, latitude, longitude,
             infos_pratiques, g.utilisateur["id"], categorie_id),
        )
        base.commit()
        return redirect(url_for("accueil"))

    return render_template(
        "ajouter_lieu.html", categories=categories, gouvernorats=GOUVERNORATS
    )