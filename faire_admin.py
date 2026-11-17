import sqlite3

base = sqlite3.connect("wanderly.db")
base.execute("UPDATE utilisateur SET role = 'admin' WHERE pseudo = 'testadmin'")
base.commit()
print("testadmin est maintenant admin.")