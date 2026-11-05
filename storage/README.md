# Couche de stockage

`governance.db` conserve les demandes et les itérations d'analyse, les résultats des cinq agents, les anomalies, classifications, constats de sécurité, relations de lignage et descriptions du dictionnaire. Chaque résultat est rattaché à une itération, elle-même rattachée à une demande. Les validations enregistrent le réviseur, son rôle, sa décision et son commentaire ; `audit_log` conserve les actions importantes.

Le dictionnaire de données garantit une seule entrée par paire table/colonne. Les clés étrangères et contraintes d'énumération protègent la cohérence des métadonnées.

Pour initialiser la base :

```bash
python -c "from storage.db import init_db; init_db()"
```

`seed_demo_data.py` crée `demo_data.db`, une base métier distincte avec des données fictives et des défauts de qualité intentionnels. Les commandes suivantes lancent les tests depuis le dossier parent :

```bash
python -m storage.seed_demo_data
pytest storage/test_storage.py
```

Les connexions CRUD sont fournies par `get_connection()` et les modifications sont à valider avec `connection.commit()` (ou un gestionnaire `with connection:`).
