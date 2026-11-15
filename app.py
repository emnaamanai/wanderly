import os
import sqlite3
import uuid
from datetime import date
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, session, g, abort, flash
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "wanderly-cle-secrete-a-changer-123"

import db
db.init_app(app)


# ---------- Réglages ----------
DOSSIER_PHOTOS = os.path.join(app.root_path, "static", "uploads")
os.makedirs(DOSSIER_PHOTOS, exist_ok=True)
EXTENSIONS_AUTORISEES = {"jpg", "jpeg", "png", "webp"}
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 Mo maximum par envoi

LIEUX_PAR_PAGE = 12

GOUVERNORATS = [
    "Ariana", "Béja", "Ben Arous", "Bizerte", "Gabès", "Gafsa", "Jendouba",
    "Kairouan", "Kasserine", "Kébili", "Le Kef", "Mahdia", "La Manouba",
    "Médenine", "Monastir", "Nabeul", "Sfax", "Sidi Bouzid", "Siliana",
    "Sousse", "Tataouine", "Tozeur", "Tunis", "Zaghouan",
]
MOTIFS = ["fermé", "doublon", "information fausse", "contenu inapproprié"]
MOTIFS_AVIS = ["information fausse", "contenu inapproprié"]
SAISONS = ["printemps", "été", "automne", "hiver", "toute l'année"]

@app.errorhandler(413)
def fichier_trop_lourd(erreur):
    return "Les fichiers envoyés sont trop lourds (10 Mo maximum).", 413


# ---------- Fonctions utiles ----------
def en_nombre(texte):
    try:
        return float(texte)
    except ValueError:
        return None


def enregistrer_photos(fichiers, lieu_id, base):
    for fichier in fichiers[:5]:
        if not fichier or fichier.filename == "":
            continue
        if "." not in fichier.filename:
            continue
        extension = fichier.filename.rsplit(".", 1)[1].lower()
        if extension not in EXTENSIONS_AUTORISEES:
            continue
        nom_fichier = uuid.uuid4().hex + "." + extension
        fichier.save(os.path.join(DOSSIER_PHOTOS, nom_fichier))
        base.execute(
            "INSERT INTO photo (nom_fichier, lieu_id) VALUES (?, ?)",
            (nom_fichier, lieu_id),
        )
    base.commit()
def effacer_lieu(base, lieu_id):
    """Supprime les photos (fichiers) d'un lieu, puis le lieu lui-même."""
    photos = base.execute(
        "SELECT nom_fichier FROM photo WHERE lieu_id = ?", (lieu_id,)
    ).fetchall()
    for photo in photos:
        chemin = os.path.join(DOSSIER_PHOTOS, photo["nom_fichier"])
        if os.path.exists(chemin):
            os.remove(chemin)

    base.execute("DELETE FROM lieu WHERE id = ?", (lieu_id,))
    base.commit()

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


# ---------- Accueil ----------
@app.route("/")
def accueil():
    base = db.get_db()

    categorie_id = request.args.get("categorie", "")
    region = request.args.get("region", "")
    prix_min = request.args.get("prix_min", "")
    prix_max = request.args.get("prix_max", "")
    page = request.args.get("page", 1, type=int)

    tags = base.execute("SELECT * FROM tag_ambiance ORDER BY nom").fetchall()
    ids_valides = {str(t["id"]) for t in tags}
    tags_choisis = [t for t in request.args.getlist("tags") if t in ids_valides]

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

    if tags_choisis:
        depuis += (
            " AND lieu.id IN (SELECT lieu_id FROM lieu_tag WHERE tag_id IN ("
            + ",".join("?" * len(tags_choisis))
            + ") GROUP BY lieu_id HAVING COUNT(DISTINCT tag_id) = ?)"
        )
        parametres.extend(tags_choisis)
        parametres.append(len(tags_choisis))

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
        "tags": tags_choisis,
    }

    return render_template(
        "index.html",
        lieux=lieux,
        categories=categories,
        gouvernorats=GOUVERNORATS,
        tags=tags,
        tags_choisis=tags_choisis,
        categorie_id=categorie_id,
        region=region,
        prix_min=prix_min,
        prix_max=prix_max,
        prix_le_plus_haut=prix_le_plus_haut,
        page=page,
        nb_pages=nb_pages,
        filtres=filtres,
    )


# ---------- Comptes ----------
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


# ---------- Lieux ----------
@app.route("/lieux/ajouter", methods=["GET", "POST"])
@login_required
def ajouter_lieu():
    base = db.get_db()
    categories = base.execute("SELECT * FROM categorie ORDER BY nom").fetchall()
    tags = base.execute("SELECT * FROM tag_ambiance ORDER BY nom").fetchall()

    if request.method == "POST":
        nom = request.form["nom"].strip()
        categorie_id = request.form["categorie"]
        region = request.form["region"]
        description = request.form["description"].strip()
        infos_pratiques = request.form["infos_pratiques"].strip()
        prix = en_nombre(request.form["prix"])
        latitude = en_nombre(request.form["latitude"])
        longitude = en_nombre(request.form["longitude"])

        ids_valides = {str(t["id"]) for t in tags}
        tags_choisis = [t for t in request.form.getlist("tags") if t in ids_valides]

        if (not nom or region not in GOUVERNORATS or prix is None or prix < 0
                or latitude is None or longitude is None):
            return render_template(
                "ajouter_lieu.html",
                erreur="Merci de remplir correctement tous les champs obligatoires.",
                categories=categories,
                tags=tags,
                gouvernorats=GOUVERNORATS,
            )

        curseur = base.execute(
            "INSERT INTO lieu (nom, description, region, prix, latitude, longitude, "
            "infos_pratiques, auteur_id, categorie_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (nom, description, region, prix, latitude, longitude,
             infos_pratiques, g.utilisateur["id"], categorie_id),
        )
        lieu_id = curseur.lastrowid

        for tag_id in tags_choisis:
            base.execute(
                "INSERT INTO lieu_tag (lieu_id, tag_id) VALUES (?, ?)",
                (lieu_id, tag_id),
            )
        base.commit()

        enregistrer_photos(request.files.getlist("photos"), lieu_id, base)
        return redirect(url_for("voir_lieu", lieu_id=lieu_id))

    return render_template(
        "ajouter_lieu.html",
        categories=categories,
        tags=tags,
        gouvernorats=GOUVERNORATS,
    )


@app.route("/lieux/<int:lieu_id>")
def voir_lieu(lieu_id):
    base = db.get_db()
    lieu = base.execute(
        "SELECT lieu.*, categorie.nom AS categorie, utilisateur.pseudo AS auteur "
        "FROM lieu "
        "JOIN categorie ON lieu.categorie_id = categorie.id "
        "JOIN utilisateur ON lieu.auteur_id = utilisateur.id "
        "WHERE lieu.id = ?",
        (lieu_id,),
    ).fetchone()

    if lieu is None:
        abort(404)

    photos = base.execute(
        "SELECT * FROM photo WHERE lieu_id = ? ORDER BY id", (lieu_id,)
    ).fetchall()

    tags = base.execute(
        "SELECT tag_ambiance.nom FROM lieu_tag "
        "JOIN tag_ambiance ON lieu_tag.tag_id = tag_ambiance.id "
        "WHERE lieu_tag.lieu_id = ? ORDER BY tag_ambiance.nom",
        (lieu_id,),
    ).fetchall()

    avis = base.execute(
        "SELECT avis.*, utilisateur.pseudo AS auteur FROM avis "
        "JOIN utilisateur ON avis.auteur_id = utilisateur.id "
        "WHERE avis.lieu_id = ? ORDER BY avis.id DESC",
        (lieu_id,),
    ).fetchall()

    stats = base.execute(
        "SELECT COUNT(*) AS nb, AVG(note) AS moyenne FROM avis WHERE lieu_id = ?",
        (lieu_id,),
    ).fetchone()

    peut_noter = False
    if g.utilisateur and g.utilisateur["id"] != lieu["auteur_id"]:
        deja = base.execute(
            "SELECT 1 FROM avis WHERE lieu_id = ? AND auteur_id = ?",
            (lieu_id, g.utilisateur["id"]),
        ).fetchone()
        peut_noter = deja is None
    mon_statut = None
    if g.utilisateur:
        ligne = base.execute(
            "SELECT statut FROM liste_lieu WHERE utilisateur_id = ? AND lieu_id = ?",
            (g.utilisateur["id"], lieu_id),
        ).fetchone()
        if ligne:
            mon_statut = ligne["statut"]
    return render_template(
        "lieu.html",
        lieu=lieu,
        photos=photos,
        tags=tags,
        avis=avis,
        nb_avis=stats["nb"],
        moyenne=stats["moyenne"],
        peut_noter=peut_noter,
        mon_statut=mon_statut,
        aujourdhui=date.today().isoformat(),
    )


@app.route("/lieux/<int:lieu_id>/modifier", methods=["GET", "POST"])
@login_required
def modifier_lieu(lieu_id):
    base = db.get_db()
    lieu = base.execute("SELECT * FROM lieu WHERE id = ?", (lieu_id,)).fetchone()

    if lieu is None:
        abort(404)
    if lieu["auteur_id"] != g.utilisateur["id"] and g.utilisateur["role"] != "admin":
        abort(403)

    categories = base.execute("SELECT * FROM categorie ORDER BY nom").fetchall()
    tags = base.execute("SELECT * FROM tag_ambiance ORDER BY nom").fetchall()
    tags_du_lieu = {
        str(ligne["tag_id"])
        for ligne in base.execute(
            "SELECT tag_id FROM lieu_tag WHERE lieu_id = ?", (lieu_id,)
        ).fetchall()
    }

    if request.method == "POST":
        nom = request.form["nom"].strip()
        categorie_id = request.form["categorie"]
        region = request.form["region"]
        description = request.form["description"].strip()
        infos_pratiques = request.form["infos_pratiques"].strip()
        prix = en_nombre(request.form["prix"])

        ids_valides = {str(t["id"]) for t in tags}
        tags_choisis = [t for t in request.form.getlist("tags") if t in ids_valides]

        if not nom or region not in GOUVERNORATS or prix is None or prix < 0:
            return render_template(
                "modifier_lieu.html",
                erreur="Merci de remplir correctement tous les champs obligatoires.",
                lieu=lieu,
                categories=categories,
                tags=tags,
                tags_du_lieu=tags_du_lieu,
                gouvernorats=GOUVERNORATS,
            )

        base.execute(
            "UPDATE lieu SET nom = ?, description = ?, region = ?, prix = ?, "
            "infos_pratiques = ?, categorie_id = ? WHERE id = ?",
            (nom, description, region, prix, infos_pratiques, categorie_id, lieu_id),
        )
        base.execute("DELETE FROM lieu_tag WHERE lieu_id = ?", (lieu_id,))
        for tag_id in tags_choisis:
            base.execute(
                "INSERT INTO lieu_tag (lieu_id, tag_id) VALUES (?, ?)",
                (lieu_id, tag_id),
            )
        base.commit()
        return redirect(url_for("voir_lieu", lieu_id=lieu_id))

    return render_template(
        "modifier_lieu.html",
        lieu=lieu,
        categories=categories,
        tags=tags,
        tags_du_lieu=tags_du_lieu,
        gouvernorats=GOUVERNORATS,
    )


@app.route("/lieux/<int:lieu_id>/supprimer", methods=["POST"])
@login_required
def supprimer_lieu(lieu_id):
    base = db.get_db()
    lieu = base.execute("SELECT * FROM lieu WHERE id = ?", (lieu_id,)).fetchone()

    if lieu is None:
        abort(404)
    if lieu["auteur_id"] != g.utilisateur["id"] and g.utilisateur["role"] != "admin":
        abort(403)

    effacer_lieu(base, lieu_id)
    return redirect(url_for("accueil"))

# ---------- Avis ----------
@app.route("/lieux/<int:lieu_id>/avis", methods=["POST"])
@login_required
def ajouter_avis(lieu_id):
    base = db.get_db()
    lieu = base.execute("SELECT * FROM lieu WHERE id = ?", (lieu_id,)).fetchone()

    if lieu is None:
        abort(404)
    if lieu["auteur_id"] == g.utilisateur["id"]:
        abort(403)

    note = request.form.get("note", type=int)
    commentaire = request.form["commentaire"].strip()

    try:
        date_visite = date.fromisoformat(request.form["date_visite"])
    except ValueError:
        abort(400)

    if note is None or not 1 <= note <= 5 or date_visite > date.today():
        abort(400)

    try:
        base.execute(
            "INSERT INTO avis (note, commentaire, date_visite, auteur_id, lieu_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (note, commentaire, date_visite.isoformat(), g.utilisateur["id"], lieu_id),
        )
        base.commit()
    except sqlite3.IntegrityError:
        pass  # il a déjà donné un avis sur ce lieu

    return redirect(url_for("voir_lieu", lieu_id=lieu_id))
@app.route("/lieux/<int:lieu_id>/liste", methods=["POST"])
@login_required
def changer_liste(lieu_id):
    base = db.get_db()
    lieu = base.execute("SELECT id FROM lieu WHERE id = ?", (lieu_id,)).fetchone()
    if lieu is None:
        abort(404)

    statut = request.form.get("statut")

    if statut == "retirer":
        base.execute(
            "DELETE FROM liste_lieu WHERE utilisateur_id = ? AND lieu_id = ?",
            (g.utilisateur["id"], lieu_id),
        )
    elif statut in ("visité", "à visiter"):
        base.execute(
            "INSERT INTO liste_lieu (utilisateur_id, lieu_id, statut) VALUES (?, ?, ?) "
            "ON CONFLICT (utilisateur_id, lieu_id) "
            "DO UPDATE SET statut = excluded.statut, date_marquage = date('now')",
            (g.utilisateur["id"], lieu_id, statut),
        )
    else:
        abort(400)

    base.commit()
    return redirect(url_for("voir_lieu", lieu_id=lieu_id))
@app.route("/mes-lieux")
@login_required
def mes_lieux():
    lignes = db.get_db().execute(
        "SELECT lieu.*, categorie.nom AS categorie, liste_lieu.statut AS statut "
        "FROM liste_lieu "
        "JOIN lieu ON liste_lieu.lieu_id = lieu.id "
        "JOIN categorie ON lieu.categorie_id = categorie.id "
        "WHERE liste_lieu.utilisateur_id = ? "
        "ORDER BY liste_lieu.date_marquage DESC, lieu.id DESC",
        (g.utilisateur["id"],),
    ).fetchall()

    visites = [l for l in lignes if l["statut"] == "visité"]
    a_visiter = [l for l in lignes if l["statut"] == "à visiter"]

    return render_template("mes_lieux.html", visites=visites, a_visiter=a_visiter)
@app.route("/lieux/<int:lieu_id>/confirmer", methods=["POST"])
@login_required
def confirmer_lieu(lieu_id):
    base = db.get_db()
    lieu = base.execute("SELECT id FROM lieu WHERE id = ?", (lieu_id,)).fetchone()
    if lieu is None:
        abort(404)

    base.execute(
        "UPDATE lieu SET nb_confirmations = nb_confirmations + 1, "
        "date_derniere_confirmation = date('now') WHERE id = ?",
        (lieu_id,),
    )
    base.commit()
    return redirect(url_for("voir_lieu", lieu_id=lieu_id))

@app.route("/lieux/<int:lieu_id>/signaler", methods=["POST"])
@login_required
def signaler_lieu(lieu_id):
    base = db.get_db()
    lieu = base.execute("SELECT id FROM lieu WHERE id = ?", (lieu_id,)).fetchone()
    if lieu is None:
        abort(404)

    motif = request.form.get("motif")
    if motif not in MOTIFS:
        abort(400)

    base.execute(
        "INSERT INTO signalement (motif, auteur_id, lieu_id) VALUES (?, ?, ?)",
        (motif, g.utilisateur["id"], lieu_id),
    )
    base.commit()
    flash("Merci, ton signalement a été envoyé. Un administrateur va le vérifier.")
    return redirect(url_for("voir_lieu", lieu_id=lieu_id))

@app.route("/avis/<int:avis_id>/signaler", methods=["POST"])
@login_required
def signaler_avis(avis_id):
    base = db.get_db()
    avis = base.execute(
        "SELECT id, lieu_id, auteur_id FROM avis WHERE id = ?", (avis_id,)
    ).fetchone()
    if avis is None:
        abort(404)
    if avis["auteur_id"] == g.utilisateur["id"]:
        abort(403)

    motif = request.form.get("motif")
    if motif not in MOTIFS_AVIS:
        abort(400)

    base.execute(
        "INSERT INTO signalement (motif, auteur_id, avis_id) VALUES (?, ?, ?)",
        (motif, g.utilisateur["id"], avis_id),
    )
    base.commit()
    flash("Merci, ton signalement a été envoyé. Un administrateur va le vérifier.")
    return redirect(url_for("voir_lieu", lieu_id=avis["lieu_id"]))


@app.route("/admin/signalements")
@admin_required
def admin_signalements():
    signalements = db.get_db().execute(
        "SELECT signalement.*, "
        "utilisateur.pseudo AS auteur, "
        "lieu.nom AS lieu_nom, "
        "avis.commentaire AS avis_commentaire, avis.lieu_id AS avis_lieu_id "
        "FROM signalement "
        "JOIN utilisateur ON signalement.auteur_id = utilisateur.id "
        "LEFT JOIN lieu ON signalement.lieu_id = lieu.id "
        "LEFT JOIN avis ON signalement.avis_id = avis.id "
        "WHERE signalement.statut = 'en attente' "
        "ORDER BY signalement.id DESC"
    ).fetchall()
    return render_template("admin_signalements.html", signalements=signalements)


@app.route("/admin/signalements/<int:signalement_id>/conserver", methods=["POST"])
@admin_required
def conserver_signalement(signalement_id):
    base = db.get_db()
    curseur = base.execute(
        "UPDATE signalement SET statut = 'traité' WHERE id = ?", (signalement_id,)
    )
    if curseur.rowcount == 0:
        abort(404)
    base.commit()
    flash("Signalement traité : le contenu est conservé.")
    return redirect(url_for("admin_signalements"))


@app.route("/admin/signalements/<int:signalement_id>/supprimer", methods=["POST"])
@admin_required
def supprimer_contenu_signale(signalement_id):
    base = db.get_db()
    s = base.execute(
        "SELECT * FROM signalement WHERE id = ?", (signalement_id,)
    ).fetchone()
    if s is None:
        abort(404)

    if s["lieu_id"] is not None:
        effacer_lieu(base, s["lieu_id"])
        flash("Lieu supprimé.")
    else:
        base.execute("DELETE FROM avis WHERE id = ?", (s["avis_id"],))
        base.commit()
        flash("Avis supprimé.")

    return redirect(url_for("admin_signalements"))


@app.route("/sorties/creer", methods=["GET", "POST"])
@login_required
def creer_sortie():
    if request.method == "POST":
        titre = request.form["titre"].strip()
        description = request.form["description"].strip()
        duree = request.form["duree"].strip()
        prix = en_nombre(request.form["prix"])
        saison = request.form["saison"]
        taille_groupe = request.form.get("taille_groupe", type=int)

        if (not titre or prix is None or prix < 0
                or (saison and saison not in SAISONS)
                or (taille_groupe is not None and taille_groupe < 1)):
            return render_template(
                "creer_sortie.html",
                erreur="Merci de remplir correctement les champs obligatoires.",
                saisons=SAISONS,
            )

        base = db.get_db()
        curseur = base.execute(
            "INSERT INTO sortie (titre, description, duree, prix, saison, "
            "taille_groupe, auteur_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (titre, description, duree, prix, saison or None,
             taille_groupe, g.utilisateur["id"]),
        )
        base.commit()
        flash("Sortie créée. Ajoute maintenant les lieux de ton programme.")
        return redirect(url_for("voir_sortie", sortie_id=curseur.lastrowid))

    return render_template("creer_sortie.html", saisons=SAISONS)
def sortie_modifiable(base, sortie_id):
    """Renvoie la sortie si l'utilisateur a le droit de la modifier, sinon erreur."""
    sortie = base.execute(
        "SELECT * FROM sortie WHERE id = ?", (sortie_id,)
    ).fetchone()
    if sortie is None:
        abort(404)
    if sortie["auteur_id"] != g.utilisateur["id"] and g.utilisateur["role"] != "admin":
        abort(403)
    return sortie


@app.route("/sorties/<int:sortie_id>")
def voir_sortie(sortie_id):
    base = db.get_db()
    sortie = base.execute(
        "SELECT sortie.*, utilisateur.pseudo AS auteur "
        "FROM sortie JOIN utilisateur ON sortie.auteur_id = utilisateur.id "
        "WHERE sortie.id = ?",
        (sortie_id,),
    ).fetchone()
    if sortie is None:
        abort(404)

    lieux = base.execute(
        "SELECT lieu.*, categorie.nom AS categorie, sortie_lieu.ordre AS ordre "
        "FROM sortie_lieu "
        "JOIN lieu ON sortie_lieu.lieu_id = lieu.id "
        "JOIN categorie ON lieu.categorie_id = categorie.id "
        "WHERE sortie_lieu.sortie_id = ? ORDER BY sortie_lieu.ordre",
        (sortie_id,),
    ).fetchall()

    peut_modifier = bool(
        g.utilisateur
        and (g.utilisateur["id"] == sortie["auteur_id"]
             or g.utilisateur["role"] == "admin")
    )

    disponibles = []
    if peut_modifier:
        disponibles = base.execute(
            "SELECT id, nom, region FROM lieu "
            "WHERE id NOT IN (SELECT lieu_id FROM sortie_lieu WHERE sortie_id = ?) "
            "ORDER BY nom",
            (sortie_id,),
        ).fetchall()

    return render_template(
        "sortie.html",
        sortie=sortie,
        lieux=lieux,
        peut_modifier=peut_modifier,
        disponibles=disponibles,
    )


@app.route("/sorties/<int:sortie_id>/lieux", methods=["POST"])
@login_required
def ajouter_lieu_sortie(sortie_id):
    base = db.get_db()
    sortie_modifiable(base, sortie_id)

    lieu_id = request.form.get("lieu_id", type=int)
    lieu = base.execute("SELECT id FROM lieu WHERE id = ?", (lieu_id,)).fetchone()
    if lieu is None:
        abort(400)

    ordre = base.execute(
        "SELECT COALESCE(MAX(ordre), 0) + 1 FROM sortie_lieu WHERE sortie_id = ?",
        (sortie_id,),
    ).fetchone()[0]

    try:
        base.execute(
            "INSERT INTO sortie_lieu (sortie_id, lieu_id, ordre) VALUES (?, ?, ?)",
            (sortie_id, lieu_id, ordre),
        )
        base.commit()
    except sqlite3.IntegrityError:
        pass  # ce lieu est déjà dans la sortie

    return redirect(url_for("voir_sortie", sortie_id=sortie_id))


@app.route("/sorties/<int:sortie_id>/lieux/<int:lieu_id>/retirer", methods=["POST"])
@login_required
def retirer_lieu_sortie(sortie_id, lieu_id):
    base = db.get_db()
    sortie_modifiable(base, sortie_id)

    base.execute(
        "DELETE FROM sortie_lieu WHERE sortie_id = ? AND lieu_id = ?",
        (sortie_id, lieu_id),
    )
    base.commit()
    return redirect(url_for("voir_sortie", sortie_id=sortie_id))
@app.route("/sorties")
def liste_sorties():
    sorties = db.get_db().execute(
        "SELECT sortie.*, utilisateur.pseudo AS auteur, "
        "COUNT(sortie_lieu.lieu_id) AS nb_lieux "
        "FROM sortie "
        "JOIN utilisateur ON sortie.auteur_id = utilisateur.id "
        "LEFT JOIN sortie_lieu ON sortie_lieu.sortie_id = sortie.id "
        "GROUP BY sortie.id "
        "ORDER BY sortie.id DESC"
    ).fetchall()
    return render_template("sorties.html", sorties=sorties)
