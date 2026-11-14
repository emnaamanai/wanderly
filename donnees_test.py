import sqlite3

base = sqlite3.connect("wanderly.db")
base.execute("PRAGMA foreign_keys = ON")

lieux = [
    ("Parc du Belvédère", "Grand parc avec vue sur Tunis et un petit zoo.",
     "Tunis", "gratuit", 36.8222, 10.1736, "Ouvert toute la journée.", 1, 3),
    ("Sidi Bou Saïd", "Village blanc et bleu au bord de la mer.",
     "Tunis", "gratuit", 36.8702, 10.3414, "Mieux vaut y aller tôt le matin.", 1, 3),
    ("Café des Nattes", "Café traditionnel avec terrasse.",
     "Tunis", "économique", 36.8704, 10.3416, "Prévoir de la monnaie.", 1, 1),
    ("Plage de Hammamet", "Longue plage de sable fin.",
     "Nabeul", "gratuit", 36.4000, 10.6150, "Parking à proximité.", 1, 2),
    ("Vieux port de Bizerte", "Balade au bord de l'eau et restaurants de poisson.",
     "Bizerte", "moyen", 37.2744, 9.8739, "Parking payant en été.", 1, 6),
    ("Jebel Zaghouan", "Randonnée avec vue sur la région.",
     "Zaghouan", "gratuit", 36.3900, 10.1200, "Prévoir de l'eau et de bonnes chaussures.", 1, 4),
]

for lieu in lieux:
    base.execute(
        "INSERT INTO lieu (nom, description, region, budget, latitude, longitude, "
        "infos_pratiques, auteur_id, categorie_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        lieu,
    )

base.commit()
print(len(lieux), "lieux ajoutés.")