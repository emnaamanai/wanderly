import sqlite3

base = sqlite3.connect("wanderly.db")
base.executescript("""
PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS sortie_lieu;
DROP TABLE IF EXISTS sortie;

CREATE TABLE sortie (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    titre         TEXT NOT NULL,
    description   TEXT,
    duree         TEXT,
    prix          REAL NOT NULL DEFAULT 0 CHECK (prix >= 0),
    saison        TEXT CHECK (saison IN ('printemps', 'été', 'automne', 'hiver', 'toute l''année')),
    taille_groupe INTEGER,
    auteur_id     INTEGER NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE
);

CREATE TABLE sortie_lieu (
    sortie_id INTEGER NOT NULL REFERENCES sortie(id) ON DELETE CASCADE,
    lieu_id   INTEGER NOT NULL REFERENCES lieu(id) ON DELETE CASCADE,
    ordre     INTEGER NOT NULL,
    PRIMARY KEY (sortie_id, lieu_id)
);

PRAGMA foreign_keys = ON;
""")
print("Tables sortie et sortie_lieu recréées.")