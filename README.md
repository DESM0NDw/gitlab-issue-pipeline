# gitlab-issue-pipeline

Setup-Script für die dreiteilige GitLab Issue Automation Pipeline.

## Pipeline-Übersicht

```
Neues Issue
    → gitlab-issue-bot       (type::* + ki-ersteinschätzung::*)
    → gitlab-issue-analyzer  (+ bot::prio-gesetzt)
    → gitlab-issue-solver    (+ bot::lösungsvorschlag, nur type::bug)
```

| Bot | Repo | Aufgabe |
|-----|------|---------|
| gitlab-issue-bot | [DESM0NDw/gitlab-issue-bot](https://github.com/DESM0NDw/gitlab-issue-bot) | Klassifiziert neue Issues per LLM in Echtzeit |
| gitlab-issue-analyzer | [DESM0NDw/gitlab-issue-analyzer](https://github.com/DESM0NDw/gitlab-issue-analyzer) | Tägliche Duplikat-Erkennung + KI-Prioritätsliste |
| gitlab-issue-solver | [DESM0NDw/gitlab-issue-solver](https://github.com/DESM0NDw/gitlab-issue-solver) | Schlägt Code-Fixes für Bugs vor (mit Diff) |

## Setup für ein neues Projekt

### 1. Drei Bots deployen

Jeden Bot einmalig klonen, `.env` befüllen und starten:

```bash
git clone https://github.com/DESM0NDw/gitlab-issue-bot
git clone https://github.com/DESM0NDw/gitlab-issue-analyzer
git clone https://github.com/DESM0NDw/gitlab-issue-solver
```

`.env.example` aus diesem Repo als Vorlage verwenden:

```bash
cp .env.example gitlab-issue-bot/.env
cp .env.example gitlab-issue-analyzer/.env
cp .env.example gitlab-issue-solver/.env
# jeweils anpassen, dann:
docker compose up -d --build
```

### 2. GitLab-Projekt einrichten

Das Setup-Script legt alle Labels an und registriert die Webhooks:

```bash
pip install requests

python setup.py \
  --gitlab-url https://gitlab.com \
  --token YOUR_GITLAB_TOKEN \
  --project-id YOUR_PROJECT_ID \
  --bot-url https://gitlab-bot.your-domain.com \
  --solver-url https://issue-solver.your-domain.com \
  --webhook-secret YOUR_SECRET
```

### 3. Bestehende Issues klassifizieren (optional)

```bash
curl -X POST "https://gitlab-bot.your-domain.com/backfill?project_id=YOUR_PROJECT_ID"
```

## Mehrere Projekte

Der Analyzer unterstützt mehrere Projekt-IDs gleichzeitig:

```env
GITLAB_PROJECT_ID=12345,67890,11223
```

Issue-Bot und Solver sind bereits multi-project-fähig (project_id aus Webhook-Payload).
Das Setup-Script einmalig pro Projekt ausführen.

## Label-Schema

| Label | Gesetzt von | Bedeutung |
|-------|-------------|-----------|
| `type::*` | issue-bot | Art des Issues (bug/feature/question/...) |
| `ki-ersteinschätzung::*` | issue-bot | KI-Erstpriorität (hoch/mittel/niedrig) |
| `bot::prio-gesetzt` | analyzer | Issue wurde analysiert und priorisiert |
| `bot::lösungsvorschlag` | solver | Lösungsvorschlag als Kommentar vorhanden |
| `bot::duplikat-prüfen` | analyzer | Mögliches Duplikat erkannt |
| `bot::prioritätsliste` | analyzer | Internes Issue mit KI-Prioritätsliste |
