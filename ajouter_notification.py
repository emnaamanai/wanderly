import sqlite3

base = sqlite3.connect("wanderly.db")
base.execute("""
CREATE TABLE IF NOT EXISTS notification (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    destinataire_id INTEGER NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
    acteur_id       INTEGER NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
    type            TEXT NOT NULL CHECK (type IN ('abonnement', 'avis')),
    lieu_id         INTEGER REFERENCES lieu(id) ON DELETE CASCADE,
    lue             INTEGER NOT NULL DEFAULT 0,
    date_creation   TEXT NOT NULL DEFAULT (date('now')),
    CHECK (destinataire_id <> acteur_id)
)
""")
base.commit()
print("Table notification créée.")