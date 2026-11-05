"""Génère une base métier fictive comportant des défauts de qualité."""

from pathlib import Path
import random
import sqlite3


_DEFAULT_DB_PATH = Path(__file__).with_name("demo_data.db")

_PRENOMS = (
    "Camille",
    "Alex",
    "Nora",
    "Louis",
    "Ines",
    "Hugo",
    "Lea",
    "Noah",
    "Maya",
    "Eliott",
    "Sarah",
    "Adam",
)
_NOMS = (
    "Martin",
    "Bernard",
    "Petit",
    "Robert",
    "Richard",
    "Durand",
    "Dubois",
    "Moreau",
    "Laurent",
    "Simon",
    "Michel",
    "Lefebvre",
)
_VILLES = ("Paris", "Lyon", "Lille", "Nantes", "Bordeaux", "Toulouse")


def create_demo_data(db_path: str | Path | None = None) -> Path:
    """Crée la base de démonstration de façon reproductible et renvoie son chemin."""
    path = Path(db_path) if db_path is not None else _DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    randomizer = random.Random(2026)

    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY,
                nom TEXT,
                email TEXT,
                telephone TEXT,
                iban TEXT,
                date_naissance TEXT,
                ville TEXT
            );
            CREATE TABLE IF NOT EXISTS commandes (
                id INTEGER PRIMARY KEY,
                client_id INTEGER,
                produit_id INTEGER,
                montant REAL,
                date_commande TEXT
            );
            CREATE TABLE IF NOT EXISTS produits (
                id INTEGER PRIMARY KEY,
                libelle TEXT,
                prix REAL,
                categorie TEXT
            );
            """
        )

        # La base démo est remplaçable : chaque exécution repart du même jeu fixe.
        connection.execute("DELETE FROM commandes")
        connection.execute("DELETE FROM clients")
        connection.execute("DELETE FROM produits")

        products = (
            (1, "Carnet", 8.50, "papeterie"),
            (2, "Stylo", 2.20, "papeterie"),
            (3, "Sac", 34.90, "accessoires"),
            (4, "Gourde", 16.00, "accessoires"),
            (5, "Clavier", 59.00, "informatique"),
            (6, "Souris", 24.50, "informatique"),
            (7, "Lampe", 42.00, "maison"),
            (8, "Tasse", 11.50, "maison"),
            (9, "Livre", 19.90, "culture"),
            (10, "Puzzle", 14.90, "loisirs"),
        )
        connection.executemany(
            "INSERT INTO produits (id, libelle, prix, categorie) VALUES (?, ?, ?, ?)",
            products,
        )

        clients: list[tuple[int, str | None, str | None, str | None, str | None, str | None, str | None]] = []
        for client_id in range(1, 201):
            prenom = randomizer.choice(_PRENOMS)
            nom_famille = randomizer.choice(_NOMS)
            nom = f"{prenom} {nom_famille}"
            suffix = f"{client_id:03d}"
            email = f"{prenom.lower()}.{nom_famille.lower()}.{suffix}@exemple.test"
            telephone = f"+336{randomizer.randint(10000000, 99999999)}"
            iban = f"FR76{randomizer.randint(1000000000000000000000000, 9999999999999999999999999)}"
            annee = randomizer.randint(1940, 2005)
            date_naissance = (
                f"{annee:04d}-{randomizer.randint(1, 12):02d}-"
                f"{randomizer.randint(1, 28):02d}"
            )
            ville = randomizer.choice(_VILLES)

            if client_id % 23 == 0:
                email = "adresse-invalide"
            if client_id % 29 == 0:
                email = f"{prenom.lower()}@"
            if client_id % 17 == 0:
                telephone = None
            if client_id % 31 == 0:
                iban = None
            if client_id % 19 == 0:
                ville = None
            if client_id % 37 == 0:
                nom = None
            if client_id % 41 == 0:
                date_naissance = None

            clients.append(
                (client_id, nom, email, telephone, iban, date_naissance, ville)
            )

        # Ces lignes reprennent exactement des profils existants sous un nouvel id.
        for duplicate_id, original_id in ((201, 12), (202, 48), (203, 91), (204, 137)):
            original = clients[original_id - 1]
            clients.append((duplicate_id, *original[1:]))

        connection.executemany(
            "INSERT INTO clients "
            "(id, nom, email, telephone, iban, date_naissance, ville) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            clients,
        )

        commandes: list[tuple[int, int, int, float, str]] = []
        for commande_id in range(1, 501):
            client_id = randomizer.randint(1, 204)
            produit_id = randomizer.randint(1, len(products))
            prix = products[produit_id - 1][2]
            quantite = randomizer.randint(1, 5)
            montant = round(prix * quantite, 2)
            annee = randomizer.randint(2021, 2026)
            date_commande = (
                f"{annee:04d}-{randomizer.randint(1, 12):02d}-"
                f"{randomizer.randint(1, 28):02d}"
            )

            if commande_id % 43 == 0:
                montant = -montant
            if commande_id % 47 == 0:
                client_id = 9000 + commande_id
            if commande_id % 53 == 0:
                date_commande = "2099-12-31"
            if commande_id % 59 == 0:
                date_commande = "1900-01-01"
            if commande_id % 71 == 0:
                date_commande = "2024-02-31"

            commandes.append(
                (commande_id, client_id, produit_id, montant, date_commande)
            )

        # Pas de clés étrangères ici : les références orphelines font partie du jeu d'essai.
        connection.executemany(
            "INSERT INTO commandes "
            "(id, client_id, produit_id, montant, date_commande) "
            "VALUES (?, ?, ?, ?, ?)",
            commandes,
        )
        connection.commit()
    finally:
        connection.close()

    return path


if __name__ == "__main__":
    print(f"Base métier de démonstration créée : {create_demo_data()}")
