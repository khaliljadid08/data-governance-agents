# Govern IA

Govern IA est une plateforme académique de gouvernance des données : des agents Python analysent des tables SQLite, puis un réviseur humain valide ou rejette les résultats. L'interface Streamlit ne remplace pas les règles métier du `Supervisor` ni les accès de `storage/db.py`.

## Installation

Python 3.11 ou supérieur est requis. À la racine du dépôt :

```bash
python -m pip install -r requirements.txt
python storage/seed_demo_data.py
streamlit run app/app.py
```

Le menu latéral donne accès aux cinq vues : Nouvelle analyse, Dashboard, Anomalies, Gouvernance et Validation.

## Lancer une analyse

1. Dans **Nouvelle analyse**, déposez un ou plusieurs fichiers CSV (jusqu'à 16 Mo par fichier). Chaque fichier devient une table SQLite ; les noms de tables et colonnes sont normalisés.
2. Saisissez l'opérateur et la consigne puis lancez l'analyse. Le système exécute les agents de qualité, classification, sécurité et lignage, puis complète le dictionnaire.
3. Sans CSV, choisissez **Utiliser les données de démonstration** pour analyser les tables fictives incluses dans `storage/demo_data.db`.
4. Consultez le Dashboard, filtrez les anomalies ou explorez les métadonnées dans Gouvernance.
5. Dans Validation, un Data Steward ou Data Owner examine la synthèse, valide ou rejette avec un commentaire, et peut relancer la coordination après un rejet.

Les bases issues des CSV sont isolées dans un dossier temporaire, jamais dans le dépôt. Elles restent disponibles pendant le cycle de validation pour permettre une re-coordination, puis sont supprimées lorsque les runs qui en dépendent sont résolus. Ne téléversez pas de données confidentielles réelles. En cas d'arrêt brutal de session avant la validation, les fichiers temporaires peuvent subsister jusqu'au nettoyage de l'environnement d'exécution.

## Gemini (facultatif)

Gemini est désactivé par défaut. Pour l'activer localement, copiez `.streamlit/secrets.toml.example` vers `.streamlit/secrets.toml` et renseignez votre clé :

```toml
GEMINI_ENABLED = true
GEMINI_API_KEY = "votre-cle-api"
GEMINI_MODEL = "gemini-3.8-flash"
```

Ne publiez jamais votre clé API. Gemini ne reçoit que des métadonnées et des compteurs agrégés (noms de tables/colonnes, types, catégories, sensibilités et relations). Les lignes, valeurs, exemples d'anomalies et consignes de l'opérateur ne lui sont pas transmis. Les constats, classifications et règles de conformité sont déterminés localement ; les avis Gemini sont consultatifs et une erreur API ne bloque pas les analyses locales.

## Déploiement public

Publiez le dépôt sur GitHub puis choisissez `app/app.py` comme point d'entrée sur Streamlit Community Cloud. Configurez les secrets dans les paramètres de l'application, jamais dans le dépôt. Le rôle de reviewer est simulé et ne constitue pas une authentification ; les visiteurs d'une application publique partagent les mêmes données et peuvent déclencher des appels Gemini si celui-ci est activé. SQLite local sur Community Cloud n'offre pas de persistance garantie ; n'y stockez pas de données réelles ou confidentielles.
