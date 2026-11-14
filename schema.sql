-- ============================================================
-- Wanderly : schéma de la base de données (SQLite)
-- Chaque table correspond à une classe du diagramme de classes.
-- ============================================================

-- SQLite n'active pas les clés étrangères par défaut : il faut le demander
-- à chaque connexion (dans Flask : PRAGMA foreign_keys = ON).
PRAGMA foreign_keys = ON;

-- ---------- Utilisateurs ----------
-- Le visiteur n'a pas de compte : il n'est donc pas dans cette table.
CREATE TABLE utilisateur (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    pseudo            TEXT NOT NULL UNIQUE,
    email             TEXT NOT NULL UNIQUE,
    mot_de_passe_hash TEXT NOT NULL,               -- jamais le mot de passe en clair
    role              TEXT NOT NULL DEFAULT 'membre'
                      CHECK (role IN ('membre', 'admin')),
    est_suspendu      INTEGER NOT NULL DEFAULT 0,  -- 0 = actif, 1 = suspendu
    date_inscription  TEXT NOT NULL DEFAULT (date('now'))
);

-- ---------- Catégories et tags d'ambiance (gérés par l'administrateur) ----------
CREATE TABLE categorie (
    id  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE
);

CREATE TABLE tag_ambiance (
    id  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE
);

-- ---------- Lieux ----------
CREATE TABLE lieu (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    nom                        TEXT NOT NULL,
    description                TEXT,
    region                     TEXT NOT NULL,
    prix                       REAL NOT NULL DEFAULT 0 CHECK (prix >= 0),  -- prix moyen par personne en DT (0 = gratuit)
    latitude                   REAL NOT NULL,
    longitude                  REAL NOT NULL,
    infos_pratiques            TEXT,               -- horaires, accès, parking...
    date_creation              TEXT NOT NULL DEFAULT (date('now')),
    nb_confirmations           INTEGER NOT NULL DEFAULT 0,   -- « toujours à jour »
    date_derniere_confirmation TEXT,
    auteur_id                  INTEGER NOT NULL REFERENCES utilisateur(id),
    categorie_id               INTEGER NOT NULL REFERENCES categorie(id)
);

-- Un lieu a plusieurs tags, un tag est sur plusieurs lieux (plusieurs-à-plusieurs)
CREATE TABLE lieu_tag (
    lieu_id INTEGER NOT NULL REFERENCES lieu(id) ON DELETE CASCADE,
    tag_id  INTEGER NOT NULL REFERENCES tag_ambiance(id) ON DELETE CASCADE,
    PRIMARY KEY (lieu_id, tag_id)
);

-- La base garde seulement le nom du fichier, l'image est dans le dossier de photos
CREATE TABLE photo (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_fichier TEXT NOT NULL,
    lieu_id     INTEGER NOT NULL REFERENCES lieu(id) ON DELETE CASCADE
);

-- ---------- Avis ----------
CREATE TABLE avis (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    note          INTEGER NOT NULL CHECK (note BETWEEN 1 AND 5),
    commentaire   TEXT,
    date_visite   TEXT NOT NULL,
    date_creation TEXT NOT NULL DEFAULT (date('now')),
    auteur_id     INTEGER NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
    lieu_id       INTEGER NOT NULL REFERENCES lieu(id) ON DELETE CASCADE,
    UNIQUE (auteur_id, lieu_id)                    -- un seul avis par membre et par lieu
);
-- Règle « l'auteur d'un lieu ne peut pas le noter » : vérifiée dans Flask.

-- ---------- Listes « visité » / « à visiter » ----------
CREATE TABLE liste_lieu (
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
    lieu_id        INTEGER NOT NULL REFERENCES lieu(id) ON DELETE CASCADE,
    statut         TEXT NOT NULL CHECK (statut IN ('visité', 'à visiter')),
    date_marquage  TEXT NOT NULL DEFAULT (date('now')),
    PRIMARY KEY (utilisateur_id, lieu_id)
);

-- ---------- Sorties ----------
CREATE TABLE sortie (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    titre         TEXT NOT NULL,
    description   TEXT,
    duree         TEXT,                            -- ex. « 2 heures », « une journée »
    budget        TEXT NOT NULL DEFAULT 'gratuit'
                  CHECK (budget IN ('gratuit', 'économique', 'moyen', 'cher')),
    saison        TEXT CHECK (saison IN ('printemps', 'été', 'automne', 'hiver', 'toute l''année')),
    taille_groupe INTEGER,
    auteur_id     INTEGER NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE
);

-- Les lieux d'une sortie, dans l'ordre. Supprimer une sortie supprime seulement
-- ces lignes de liaison, jamais les lieux eux-mêmes.
CREATE TABLE sortie_lieu (
    sortie_id INTEGER NOT NULL REFERENCES sortie(id) ON DELETE CASCADE,
    lieu_id   INTEGER NOT NULL REFERENCES lieu(id) ON DELETE CASCADE,
    ordre     INTEGER NOT NULL,                    -- 1, 2, 3...
    PRIMARY KEY (sortie_id, lieu_id)
);

-- ---------- Signalements ----------
CREATE TABLE signalement (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    motif         TEXT NOT NULL
                  CHECK (motif IN ('fermé', 'doublon', 'information fausse', 'contenu inapproprié')),
    statut        TEXT NOT NULL DEFAULT 'en attente'
                  CHECK (statut IN ('en attente', 'traité')),
    date_creation TEXT NOT NULL DEFAULT (date('now')),
    auteur_id     INTEGER NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
    lieu_id       INTEGER REFERENCES lieu(id) ON DELETE CASCADE,
    avis_id       INTEGER REFERENCES avis(id) ON DELETE CASCADE,
    -- un signalement vise soit un lieu, soit un avis (exactement un des deux)
    CHECK ((lieu_id IS NULL) <> (avis_id IS NULL))
);

-- ---------- Données de départ (modifiables ensuite par l'administrateur) ----------
INSERT INTO categorie (nom) VALUES
    ('Café'), ('Plage'), ('Parc'), ('Randonnée'), ('Espace de jeux'), ('Pique-nique');

INSERT INTO tag_ambiance (nom) VALUES
    ('calme'), ('photogénique'), ('en groupe'), ('en famille'), ('vue magnifique'), ('animé');
