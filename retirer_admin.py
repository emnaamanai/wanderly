import sqlite3

base = sqlite3.connect("wanderly.db")
base.execute("UPDATE utilisateur SET role = 'membre' WHERE pseudo = 'jnik'")
base.commit()
print("jnik est de nouveau un membre normal.")