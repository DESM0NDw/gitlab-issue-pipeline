#!/usr/bin/env python3
"""
Setup script for gitlab-issue-pipeline.

Creates all required labels and registers webhooks for:
  - gitlab-issue-bot   (klassifiziert neue Issues in Echtzeit)
  - gitlab-issue-solver (schlägt Fixes für Bugs vor)

Usage:
  python setup.py \
    --gitlab-url https://gitlab.com \
    --token YOUR_TOKEN \
    --project-id YOUR_PROJECT_ID \
    --bot-url https://gitlab-bot.your-domain.com \
    --solver-url https://issue-solver.your-domain.com \
    --webhook-secret YOUR_SECRET

  # Nur Farben und fehlende Labels nachträglich aktualisieren:
  python setup.py --token YOUR_TOKEN --project-id YOUR_PROJECT_ID --update-colors
"""
import argparse
import sys
import requests

LABELS = [
    {"name": "type::bug",                    "color": "#d9534f", "description": "Bug-Report"},
    {"name": "type::feature",                "color": "#5cb85c", "description": "Feature-Anfrage"},
    {"name": "type::question",               "color": "#f0ad4e", "description": "Frage"},
    {"name": "type::documentation",          "color": "#5bc0de", "description": "Dokumentation"},
    {"name": "type::other",                  "color": "#777777", "description": "Sonstiges"},
    {"name": "ki-ersteinschätzung::hoch",    "color": "#d9534f", "description": "KI: Hohe Priorität"},
    {"name": "ki-ersteinschätzung::mittel",  "color": "#f0ad4e", "description": "KI: Mittlere Priorität"},
    {"name": "ki-ersteinschätzung::niedrig", "color": "#5cb85c", "description": "KI: Niedrige Priorität"},
    {"name": "bot::prio-gesetzt",            "color": "#0075ca", "description": "Analyzer: Priorität gesetzt"},
    {"name": "bot::lösungsvorschlag",        "color": "#7057ff", "description": "Solver: Lösungsvorschlag vorhanden"},
    {"name": "bot::duplikat-prüfen",         "color": "#e4e669", "description": "Mögliches Duplikat, bitte prüfen"},
    {"name": "bot::prioritätsliste",         "color": "#0075ca", "description": "KI-Prioritätsliste (internes Issue)"},
]


def api(gitlab_url, token, project_id, method, path, **kwargs):
    url = f"{gitlab_url}/api/v4/projects/{project_id}{path}"
    resp = requests.request(method, url, headers={"PRIVATE-TOKEN": token}, timeout=15, **kwargs)
    resp.raise_for_status()
    return resp.json() if resp.text else {}


def create_labels(gitlab_url, token, project_id):
    print("\n[Labels]")
    existing = {l["name"] for l in api(gitlab_url, token, project_id, "GET", "/labels", params={"per_page": 100})}
    for label in LABELS:
        if label["name"] in existing:
            print(f"  skip     {label['name']}")
        else:
            api(gitlab_url, token, project_id, "POST", "/labels", json=label)
            print(f"  created  {label['name']}")


def update_colors(gitlab_url, token, project_id):
    print("\n[Labels — Farben aktualisieren]")
    existing = {l["name"] for l in api(gitlab_url, token, project_id, "GET", "/labels", params={"per_page": 100})}
    for label in LABELS:
        encoded = requests.utils.quote(label["name"], safe="")
        if label["name"] in existing:
            api(gitlab_url, token, project_id, "PUT", f"/labels/{encoded}",
                json={"color": label["color"], "description": label["description"]})
            print(f"  updated  {label['name']} → {label['color']}")
        else:
            api(gitlab_url, token, project_id, "POST", "/labels", json=label)
            print(f"  created  {label['name']} → {label['color']}")


def create_webhooks(gitlab_url, token, project_id, bot_url, solver_url, webhook_secret):
    print("\n[Webhooks]")
    existing_hooks = api(gitlab_url, token, project_id, "GET", "/hooks")
    existing_urls = {h["url"] for h in existing_hooks}

    for name, url in [("issue-bot", f"{bot_url}/webhook"), ("issue-solver", f"{solver_url}/webhook")]:
        if url in existing_urls:
            print(f"  skip     {name} ({url})")
        else:
            payload = {
                "url": url,
                "issues_events": True,
                "push_events": False,
                "enable_ssl_verification": True,
            }
            if webhook_secret:
                payload["token"] = webhook_secret
            api(gitlab_url, token, project_id, "POST", "/hooks", json=payload)
            print(f"  created  {name} ({url})")


def main():
    parser = argparse.ArgumentParser(description="Setup gitlab-issue-pipeline for a GitLab project")
    parser.add_argument("--gitlab-url",     default="https://gitlab.com")
    parser.add_argument("--token",          required=True, help="GitLab Personal Access Token (scope: api)")
    parser.add_argument("--project-id",     required=True)
    parser.add_argument("--bot-url",        help="Public URL of gitlab-issue-bot")
    parser.add_argument("--solver-url",     help="Public URL of gitlab-issue-solver")
    parser.add_argument("--webhook-secret", default="", help="Shared secret for both webhooks (optional)")
    parser.add_argument("--update-colors",  action="store_true",
                        help="Nur Label-Farben und fehlende Labels aktualisieren, keine Webhooks")
    args = parser.parse_args()

    if not args.update_colors and (not args.bot_url or not args.solver_url):
        parser.error("--bot-url und --solver-url sind erforderlich (oder --update-colors für reine Label-Aktualisierung)")

    print(f"Setting up pipeline for project {args.project_id} on {args.gitlab_url}")

    try:
        if args.update_colors:
            update_colors(args.gitlab_url, args.token, args.project_id)
        else:
            create_labels(args.gitlab_url, args.token, args.project_id)
            create_webhooks(args.gitlab_url, args.token, args.project_id,
                            args.bot_url, args.solver_url, args.webhook_secret)
    except requests.HTTPError as e:
        print(f"\nFehler: {e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(1)

    if args.update_colors:
        print("\nFarben aktualisiert.")
    else:
        print("\nSetup abgeschlossen.")
        print("Nächste Schritte:")
        print("  1. .env für alle drei Bots befüllen (siehe .env.example)")
        print("  2. docker compose up -d --build in jedem Bot-Verzeichnis")
        print(f"  3. Backfill starten: curl -X POST {args.bot_url}/backfill?project_id={args.project_id}")


if __name__ == "__main__":
    main()
