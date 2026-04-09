# AntispamAdminCenter

Schlanke FastAPI-Anwendung zur zentralen Verwaltung von:

- Mandanten (`Organisationen`)
- Benutzern
- Mail-Adressen
- IP-Adressen
- Audit-Einträgen

Die Anwendung deckt den Kern des Projektantrags ab:

- mandantenfähige Verwaltung
- rollenbasiertes Berechtigungssystem
- Login mit Session
- Validierung von Eingaben
- Audit-Log für Änderungen
- Datenbereitstellung für Postfix über verwaltete Mail-/IP-Daten

## Technik

- Python 3.12+
- FastAPI
- SQLModel
- SQLite
- Argon2 für Passwort-Hashing

## Start

```powershell
cd C:\Users\Bindemann\PycharmProjects\AntispamAdminCenter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
fastapi dev app/main.py
```

Danach ist die Anwendung unter `http://127.0.0.1:8000` erreichbar.

## Wichtige `.env`-Werte

- `SESSION_SECRET_KEY`
- `ROOT_EMAIL`
- `ROOT_PASSWORD`
- `ROOT_FIRST_NAME`
- `ROOT_LAST_NAME`

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Projektstruktur

```text
app/
  core/        Konfiguration, Logging, DB, Migrationen
  models/      SQLModel-Klassen
  services/    Fachlogik
  web/         Routen, Templates, Formularhilfen
```
