import sqlite3

base = sqlite3.connect("wanderly.db")

nouveaux_tags = [
    "romantique", "entre amis", "en solo", "pour les enfants",
    "pas cher", "chic", "authentique", "moderne", "insolite",
    "nature", "loin de la foule", "coucher de soleil",
    "idéal pour travailler", "bon wifi", "musique live",
    "sportif", "aventure", "culturel", "convivial",
    "accepte les animaux", "accessible PMR", "calme et reposant",
]

for nom in nouveaux_tags:
    base.execute("INSERT OR IGNORE INTO tag_ambiance (nom) VALUES (?)", (nom,))

base.commit()
print("Tags à jour :", base.execute("SELECT COUNT(*) FROM tag_ambiance").fetchone()[0])