# Gouvernance des données

Prototype académique francophone de gouvernance des données : SQLite conserve les métadonnées, `agents/` coordonne les analyses et `app/` fournit une interface Streamlit.

## Installation locale

Python 3.11 ou supérieur est requis. Depuis la racine du projet :

```bash
python -m pip install -r requirements.txt
python storage/seed_demo_data.py
streamlit run app/app.py
```

Le jeu métier est fictif et contient des anomalies volontaires. L'application initialise `storage/governance.db` au démarrage. Ces fichiers de base de données sont exclus du dépôt ; le jeu métier démo est regénéré automatiquement s'il manque.

## Activer Gemini (facultatif)

Créez une clé API dans [Google AI Studio](https://aistudio.google.com/apikey). Pour un usage local, copiez `.streamlit/secrets.toml.example` vers `.streamlit/secrets.toml`, puis renseignez :

```toml
GEMINI_ENABLED = true
GEMINI_API_KEY = "votre-cle-api"
GEMINI_MODEL = "gemini-3.8-flash"
```

Ne publiez jamais la vraie clé. `.streamlit/secrets.toml` est ignoré par Git. Gemini peut enrichir les résultats des agents Qualité, Classification, Sécurité et Lignage, produire les descriptions du dictionnaire et rédiger un avis sur la synthèse. Sans activation et clé, les analyses locales et les gabarits de description continuent de fonctionner.

Les appels ne contiennent que des métadonnées : noms de tables et de colonnes, types SQL, catégories, niveaux de sensibilité, types de relations et compteurs agrégés. Aucune valeur de ligne, donnée personnelle, exemple d'anomalie ou consigne libre de l'opérateur n'est envoyé. Les avis Gemini sont consultatifs : règles de qualité, classifications, contrôles d'accès, résultats enregistrés et décision du reviewer restent déterminés localement. Une erreur ou une indisponibilité de l'API est affichée sans annuler les résultats déterministes.

Pour le script CLI, configurez les variables d'environnement `GEMINI_ENABLED=true`, `GEMINI_API_KEY` et, facultativement, `GEMINI_MODEL` avant d'exécuter `python -m agents.run_pipeline` depuis la racine du projet. La documentation peut déclencher un appel par colonne, en plus des avis des agents et de la synthèse ; surveillez les quotas et coûts associés.


## Publication publique et QR code

1. Créez un dépôt GitHub et publiez-y le projet (sans `storage/*.db` ni `.streamlit/secrets.toml`).
2. Connectez-vous à [Streamlit Community Cloud](https://share.streamlit.io/), choisissez **Create app**, puis le dépôt, la branche et `app/app.py` comme fichier d'entrée.
3. Si Gemini est souhaité, ouvrez **Advanced settings → Secrets** et ajoutez les trois paramètres TOML ci-dessus avec votre vraie clé. Ne mettez jamais la clé dans le dépôt. Comme l'application sera publique et sans authentification, les visiteurs peuvent déclencher des appels Gemini (dont un appel par colonne du dictionnaire) ; fixez des limites d'utilisation et surveillez le quota Google.
4. Déployez et copiez l'URL publique HTTPS fournie par Streamlit.
5. Créez un QR code à partir de cette URL (par exemple avec l'outil d'insertion QR de votre présentation) et insérez l'image dans les diapositives.

**Limites de la démo publique :** le sélecteur de rôle ne fait que masquer/afficher des pages ; ce n'est pas une authentification. Toute personne ayant le lien peut consulter et modifier les données partagées. Les bases SQLite locales d'une instance Streamlit Community Cloud ne sont pas un stockage persistant garanti et peuvent être réinitialisées lors d'un redémarrage ou redéploiement. N'y placez aucune donnée réelle ou confidentielle ; pour une utilisation durable ou multi-utilisateur, migrez vers une base hébergée avec contrôle d'accès.

Ce dossier doit être publié dans votre dépôt GitHub avant de pouvoir obtenir l'URL Cloud et fabriquer le QR code.

## Démonstration en cinq étapes

1. Choisir le rôle **Opérateur** et ouvrir **Nouvelle demande**.
2. Saisir une consigne, choisir les tables métier et activer les agents.
3. Lancer l'analyse et consulter le suivi ; la documentation s'exécute après les agents spécialisés.
4. Explorer **Résultats** et **Dictionnaire de données**.
5. Passer au rôle **Data Steward** ou **Data Owner**, valider ou rejeter avec un commentaire, puis essayer la re-coordination et consulter **Historique et audit**.
