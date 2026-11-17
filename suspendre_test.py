import sqlite3

PSEUDO = "testsusp"
VALEUR = 1  # 1 = suspendre, 0 = réactiver

base = sqlite3.connect("wanderly.db")
base.execute("UPDATE utilisateur SET est_suspendu = ? WHERE pseudo = ?", (VALEUR, PSEUDO))
base.commit()
print(PSEUDO, "-> est_suspendu =", VALEUR)