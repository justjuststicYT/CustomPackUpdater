#!/usr/bin/env python3
"""CustomPack Updater - Release-Automatisierung fuer GitHub Actions.

Zwei Schritte (vom Workflow nacheinander aufgerufen):

  prepare   Prueft die ZIP in resourcepack/, berechnet SHA-256 und die neue
            Versionsnummer (+0.0.1) und gibt alles als Step-Outputs aus.
            Schreibt NICHTS ins Repository.
  finalize  Schreibt latest.json und version.txt. Wird erst aufgerufen,
            nachdem die Release erfolgreich erstellt und geprueft wurde.

Dadurch kann bei einem Fehler nie eine ungueltige latest.json entstehen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import quote

ROOT = Path(os.environ.get("CPU_REPO_ROOT") or Path(__file__).resolve().parent.parent)
PACK_DIR = ROOT / "resourcepack"
VERSION_FILE = ROOT / "version.txt"
LATEST_FILE = ROOT / "latest.json"

DEFAULT_MC_VERSIONS = ["26.2"]
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
FILE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.zip$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_ENTRIES = 200_000
MAX_UNCOMPRESSED = 2 * 1024**3  # 2 GiB


class UpdateError(Exception):
    """Fehler mit verstaendlicher deutscher Meldung."""


def log(message: str) -> None:
    print(f"[CustomPack] {message}", flush=True)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_entry_name(name: str) -> None:
    """Schutz vor ZIP-Slip und unsinnigen Pfaden."""
    if (
        not name
        or "\x00" in name
        or "\\" in name
        or name.startswith("/")
        or (len(name) > 1 and name[1] == ":")
        or ".." in name.split("/")
    ):
        raise UpdateError(
            f"Die ZIP enthaelt einen unsicheren Pfad ('{name}'). "
            "Bitte erstelle die ZIP neu."
        )


def validate_zip(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if not infos:
                raise UpdateError("Die ZIP-Datei ist leer.")
            if len(infos) > MAX_ENTRIES:
                raise UpdateError("Die ZIP-Datei enthaelt unplausibel viele Dateien.")
            total = 0
            names = set()
            nested_meta = None
            for info in infos:
                check_entry_name(info.filename)
                total += info.file_size
                if total > MAX_UNCOMPRESSED:
                    raise UpdateError("Die ZIP-Datei ist entpackt unplausibel gross.")
                names.add(info.filename)
                if info.filename.endswith("/pack.mcmeta") and nested_meta is None:
                    nested_meta = info.filename
            bad = archive.testzip()
            if bad is not None:
                raise UpdateError(f"Die ZIP-Datei ist beschaedigt (Datei: {bad}).")
            if "pack.mcmeta" not in names:
                hint = ""
                if nested_meta:
                    folder = nested_meta.rsplit("/", 1)[0]
                    hint = (
                        f" Sie liegt im Unterordner '{folder}'. Packe den INHALT des "
                        "Ordners (nicht den Ordner selbst) in die ZIP."
                    )
                raise UpdateError(
                    "In der ZIP fehlt die Datei pack.mcmeta im obersten Ordner." + hint
                )
            try:
                meta = json.loads(archive.read("pack.mcmeta").decode("utf-8-sig"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise UpdateError(f"pack.mcmeta ist kein gueltiges JSON: {exc}") from exc
            if not isinstance(meta, dict) or not isinstance(meta.get("pack"), dict):
                raise UpdateError("pack.mcmeta enthaelt keinen gueltigen 'pack'-Eintrag.")
    except zipfile.BadZipFile as exc:
        raise UpdateError(f"Die Datei ist keine gueltige ZIP-Datei: {exc}") from exc
    except OSError as exc:
        raise UpdateError(f"Die ZIP-Datei konnte nicht gelesen werden: {exc}") from exc


def find_pack_zip() -> Path:
    zips = sorted(p for p in PACK_DIR.glob("*.zip") if p.is_file())
    if not zips:
        raise UpdateError("Im Ordner 'resourcepack' liegt keine ZIP-Datei.")
    if len(zips) > 1:
        names = ", ".join(p.name for p in zips)
        raise UpdateError(
            f"Im Ordner 'resourcepack' liegen {len(zips)} ZIP-Dateien ({names}). "
            "Es darf genau EINE sein."
        )
    zip_path = zips[0]
    if not FILE_NAME_RE.match(zip_path.name):
        raise UpdateError(
            f"Der Dateiname '{zip_path.name}' ist nicht erlaubt. Erlaubt sind nur "
            "Buchstaben, Zahlen, Punkt, Unterstrich und Bindestrich (keine Leerzeichen), "
            "z. B. CustomPack.zip."
        )
    return zip_path


def read_version() -> str:
    if not VERSION_FILE.exists():
        log("WARNUNG: version.txt fehlt - starte mit 1.0.0.")
        return "1.0.0"
    value = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not VERSION_RE.match(value):
        raise UpdateError(
            f"version.txt enthaelt '{value}'. Erwartet wird das Format 1.0.0 (drei Zahlen)."
        )
    return value


def bump_patch(version: str) -> str:
    major, minor, patch = (int(part) for part in VERSION_RE.match(version).groups())
    return f"{major}.{minor}.{patch + 1}"


def load_latest() -> dict | None:
    if not LATEST_FILE.exists():
        return None
    try:
        data = json.loads(LATEST_FILE.read_text(encoding="utf-8"))
    except ValueError as exc:
        log(f"WARNUNG: Bestehende latest.json ist ungueltig ({exc}) - wird ersetzt.")
        return None
    return data if isinstance(data, dict) else None


def write_outputs(values: dict[str, str]) -> None:
    target = os.environ.get("GITHUB_OUTPUT")
    lines = "".join(f"{key}={value}\n" for key, value in values.items())
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(lines)
    else:
        print(lines, end="")


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def cmd_prepare() -> None:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not REPO_RE.match(repo):
        raise UpdateError("GITHUB_REPOSITORY fehlt oder ist ungueltig (Skript nur in GitHub Actions starten).")

    zip_path = find_pack_zip()
    log(f"Gefundene ZIP: {zip_path.name} ({zip_path.stat().st_size} Bytes)")
    validate_zip(zip_path)
    log("ZIP-Struktur ist in Ordnung (pack.mcmeta vorhanden, keine unsicheren Pfade).")

    digest = sha256_of(zip_path)
    log(f"SHA-256: {digest}")

    latest = load_latest()
    if latest and str(latest.get("sha256", "")).lower() == digest and latest.get("file_name") == zip_path.name:
        log("Diese ZIP ist bereits veroeffentlicht - es wird keine neue Release erstellt.")
        write_outputs({"skip": "true"})
        return

    current = read_version()
    new_version = bump_patch(current)
    log(f"Version: {current} -> {new_version}")

    file_name = zip_path.name
    write_outputs(
        {
            "skip": "false",
            "version": new_version,
            "tag": f"v{new_version}",
            "file_name": file_name,
            "sha256": digest,
            "download_url": f"https://github.com/{repo}/releases/download/v{new_version}/{quote(file_name)}",
        }
    )


def cmd_finalize(args: argparse.Namespace) -> None:
    if not VERSION_RE.match(args.version):
        raise UpdateError(f"Ungueltige Version: {args.version}")
    if not FILE_NAME_RE.match(args.file_name):
        raise UpdateError(f"Ungueltiger Dateiname: {args.file_name}")
    if not SHA_RE.match(args.sha256):
        raise UpdateError("Ungueltiger SHA-256-Hash.")
    if not args.download_url.startswith("https://"):
        raise UpdateError("Die Download-URL muss mit https:// beginnen.")

    zip_path = PACK_DIR / args.file_name
    if not zip_path.is_file() or sha256_of(zip_path) != args.sha256:
        raise UpdateError("Die ZIP hat sich seit der Pruefung veraendert - Abbruch.")

    previous = load_latest() or {}
    versions = previous.get("minecraft_versions")
    if not (isinstance(versions, list) and versions and all(isinstance(v, str) for v in versions)):
        versions = list(DEFAULT_MC_VERSIONS)

    manifest = {
        "version": args.version,
        "download_url": args.download_url,
        "file_name": args.file_name,
        "sha256": args.sha256,
        "minecraft_versions": versions,
    }
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    json.loads(text)  # Gegenprobe: muss wieder lesbar sein

    atomic_write(LATEST_FILE, text)
    atomic_write(VERSION_FILE, args.version + "\n")
    log(f"latest.json und version.txt auf {args.version} aktualisiert.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    fin = sub.add_parser("finalize")
    for name in ("version", "file-name", "sha256", "download-url"):
        fin.add_argument(f"--{name}", required=True)
    args = parser.parse_args()

    try:
        if args.command == "prepare":
            cmd_prepare()
        else:
            cmd_finalize(args)
    except UpdateError as exc:
        print(f"::error::{exc}", flush=True)
        log(f"FEHLER: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
