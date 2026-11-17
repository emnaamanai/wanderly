import sqlite3

base = sqlite3.connect("wanderly.db")
base.execute("PRAGMA foreign_keys = ON")

# Test 3 : se notifier soi-même (doit échouer)
try:
    base.execute(
        "INSERT INTO notification (destinataire_id, acteur_id, type) VALUES (1, 1, 'abonnement')"
    )
    print("Test 3 : PROBLÈME, l'insertion a réussi")
except sqlite3.IntegrityError as e:
    print("Test 3 : refusé comme prévu ->", e)

# Test 4 : type inconnu (doit échouer)
try:
    base.execute(
        "INSERT INTO notification (destinataire_id, acteur_id, type) VALUES (1, 2, 'bonjour')"
    )
    print("Test 4 : PROBLÈME, l'insertion a réussi")
except sqlite3.IntegrityError as e:
    print("Test 4 : refusé comme prévu ->", e)

base.rollback()
