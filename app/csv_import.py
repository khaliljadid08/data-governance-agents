"""Import sécurisé de fichiers CSV dans une base SQLite temporaire."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from contextlib import closing
import io
import logging
from pathlib import Path
import re
import sqlite3
import tempfile
import unicodedata
from collections.abc import Sequence
from typing import Any

import pandas as pd


logger = logging.getLogger(__name__)
TAILLE_MAX_OCTETS = 16 * 1024 * 1024
_PREFIXE_TEMPORAIRE = "governia-csv-"


class CsvImportError(ValueError):
    """Signale un fichier CSV invalide ou impossible à importer."""


@dataclass(frozen=True)
class CsvImportResult:
    """Décrit la base temporaire créée à partir des fichiers importés."""

    db_path: Path
    table_names: tuple[str, ...]


def _nettoyer_identifiant(value: str, prefixe: str) -> str:
    """Réduit un nom à des caractères ASCII sûrs pour un identifiant SQLite."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", ascii_name)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = prefixe
    if cleaned[0].isdigit():
        cleaned = f"{prefixe}_{cleaned}"
    if cleaned.casefold().startswith("sqlite_"):
        cleaned = f"{prefixe}_{cleaned}"
    return cleaned[:120]


def _identifiants_uniques(names: Sequence[str], prefixe: str) -> list[str]:
    """Nettoie des identifiants en ajoutant un suffixe en cas de collision."""
    result: list[str] = []
    seen: set[str] = set()
    for raw_name in names:
        base = _nettoyer_identifiant(str(raw_name), prefixe)
        candidate = base
        suffix = 2
        while candidate.casefold() in seen:
            candidate = f"{base[:110]}_{suffix}"
            suffix += 1
        seen.add(candidate.casefold())
        result.append(candidate)
    return result


def _delimiter(data: str) -> str:
    """Détecte la virgule ou le point-virgule dans le contenu du CSV."""
    sample = "\n".join(line for line in data.splitlines()[:20] if line.strip())
    if not sample:
        return ","
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;").delimiter
    except csv.Error:
        first_line = sample.splitlines()[0]
        return ";" if first_line.count(";") > first_line.count(",") else ","


def _lire_dataframe(name: str, content: bytes) -> pd.DataFrame:
    """Décode un CSV en UTF-8 puis Latin-1 et laisse pandas le parser."""
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            decoded = content.decode("latin-1")
        except UnicodeDecodeError as erreur:
            raise CsvImportError(f"Encodage non pris en charge pour {name}.") from erreur

    try:
        dataframe = pd.read_csv(
            io.StringIO(decoded),
            sep=_delimiter(decoded),
            dtype=object,
            keep_default_na=True,
        )
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError) as erreur:
        raise CsvImportError(f"Impossible de lire le fichier {name} : {erreur}") from erreur
    if dataframe.shape[1] == 0:
        raise CsvImportError(f"Le fichier {name} ne contient aucune colonne.")
    if len(dataframe) == 0:
        raise CsvImportError(f"Le fichier {name} ne contient aucune ligne de données.")
    dataframe.columns = _identifiants_uniques(
        [str(column) for column in dataframe.columns],
        "colonne",
    )
    return dataframe


def _get_name_and_content(uploaded_file: Any) -> tuple[str, bytes]:
    """Valide l'extension et la taille avant d'extraire le contenu."""
    name = str(getattr(uploaded_file, "name", ""))
    if Path(name).suffix.casefold() != ".csv":
        raise CsvImportError(f"Le fichier « {name or 'sans nom'} » doit être un CSV.")
    content = uploaded_file.getvalue()
    if not isinstance(content, bytes):
        raise CsvImportError(f"Le contenu du fichier {name} est invalide.")
    if len(content) > TAILLE_MAX_OCTETS:
        raise CsvImportError(
            f"Le fichier {name} dépasse la limite de 16 Mo."
        )
    if not content:
        raise CsvImportError(f"Le fichier {name} est vide.")
    return name, content


def create_database(uploaded_files: Sequence[Any]) -> CsvImportResult:
    """Crée une base isolée et charge un CSV par table normalisée."""
    if not uploaded_files:
        raise CsvImportError("Sélectionnez au moins un fichier CSV.")

    file_data = [_get_name_and_content(file) for file in uploaded_files]
    dataframes = [
        (name, _lire_dataframe(name, content)) for name, content in file_data
    ]
    table_names = _identifiants_uniques(
        [Path(name).stem for name, _ in dataframes],
        "table",
    )

    temp_dir = Path(tempfile.mkdtemp(prefix=_PREFIXE_TEMPORAIRE))
    db_path = temp_dir / "import.db"
    try:
        with closing(sqlite3.connect(db_path)) as connection:
            with connection:
                for (_, dataframe), table_name in zip(dataframes, table_names):
                    dataframe.to_sql(
                        table_name,
                        connection,
                        if_exists="fail",
                        index=False,
                    )
                    logger.info(
                        "Table temporaire importée : %s (%s ligne(s)).",
                        table_name,
                        len(dataframe),
                    )
    except Exception as erreur:
        logger.exception("Échec de création de la base CSV temporaire.")
        cleanup_database(db_path)
        raise CsvImportError(f"Import CSV impossible : {erreur}") from erreur

    return CsvImportResult(db_path=db_path, table_names=tuple(table_names))


def cleanup_database(db_path: str | Path) -> None:
    """Supprime une base d'import dans un dossier Govern IA temporaire."""
    path = Path(db_path).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if (
        path.parent.parent != temp_root
        or not path.parent.name.startswith(_PREFIXE_TEMPORAIRE)
        or path.name != "import.db"
    ):
        raise ValueError("Le chemin ne désigne pas une base Govern IA temporaire.")

    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        candidate.unlink(missing_ok=True)
    path.parent.rmdir()
