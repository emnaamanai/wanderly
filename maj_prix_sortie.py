import sqlite3

base = sqlite3.connect("wanderly.db")
base.execute("ALTER TABLE sortie RENAME COLUMN prix TO prix_min")
base.execute("ALTER TABLE sortie ADD COLUMN prix_max REAL NOT NULL DEFAULT 0 CHECK (prix_max >= 0)")
base.execute("UPDATE sortie SET prix_max = prix_min")
base.commit()
print("Fourchette de prix ajoutée aux sorties.")