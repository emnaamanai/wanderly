import sqlite3

base = sqlite3.connect("wanderly.db")
base.execute("""
CREATE TABLE IF NOT EXISTS abonnement (
    suiveur_id       INTEGER NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
    suivi_id         INTEGER NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
    date_abonnement  TEXT NOT NULL DEFAULT (date('now')),
    PRIMARY KEY (suiveur_id, suivi_id),
    CHECK (suiveur_id <> suivi_id)
)
""")
base.commit()
print("Table abonnement créée.")