"""
Module de tableau de bord pour la consultation des logs prospects.
Ajoute la route /logs protégée par un code d'accès.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import Counter
import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env si présent
load_dotenv()

# ----------------------------------------------------------------------
# Configuration (obligatoire via .env)
# ----------------------------------------------------------------------
LOG_ACCESS_CODE = os.getenv("LOG_ACCESS_CODE")
if not LOG_ACCESS_CODE:
    raise RuntimeError("LOG_ACCESS_CODE doit être défini dans le fichier .env")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY doit être défini dans le fichier .env")

# Définition robuste du chemin du fichier de logs
# Le module est dans backend/, donc on remonte d'un cran pour atteindre la racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOG_FILE = BASE_DIR / "logs" / "prospects.json"

# Si PROSPECTS_LOG_FILE est défini dans .env, on l'utilise (chemin absolu ou relatif au CWD)
# Sinon on utilise le chemin par défaut basé sur l'emplacement du module
LOG_FILE = os.getenv("PROSPECTS_LOG_FILE", str(DEFAULT_LOG_FILE))

SESSION_COOKIE_NAME = "log_session"
SESSION_MAX_AGE = 24 * 3600  # 24 heures

serializer = URLSafeTimedSerializer(SECRET_KEY)

router = APIRouter(prefix="/logs", tags=["logs"])

# ----------------------------------------------------------------------
# Authentification
# ----------------------------------------------------------------------
def create_session_token() -> str:
    """Crée un token signé pour la session."""
    return serializer.dumps({"authenticated": True})

def verify_session_token(token: str) -> bool:
    """Vérifie la validité du token de session."""
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("authenticated", False)
    except (BadSignature, SignatureExpired):
        return False

def get_current_auth(request: Request) -> bool:
    """Dépendance FastAPI qui vérifie le cookie de session."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token and verify_session_token(token):
        return True
    return False

# ----------------------------------------------------------------------
# Utilitaires de lecture et de traitement
# ----------------------------------------------------------------------
def parse_ts(ts_str: str) -> datetime:
    """Convertit un timestamp ISO en datetime UTC."""
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

def sort_events(events: list) -> list:
    """Trie les événements par timestamp croissant."""
    return sorted(events, key=lambda e: parse_ts(e["ts"]))

def get_visit_duration(visit: dict) -> int:
    """Durée en secondes entre le premier et le dernier événement."""
    if not visit.get("events"):
        return 0
    events = sort_events(visit["events"])
    t0 = parse_ts(events[0]["ts"])
    t1 = parse_ts(events[-1]["ts"])
    return int((t1 - t0).total_seconds())

def get_email_from_visit(visit: dict) -> Optional[str]:
    """Récupère l'email si un événement premium_email existe."""
    for e in visit.get("events", []):
        if e["type"] == "premium_email" and "email" in e:
            return e["email"]
    return None

def recalc_stats(visits: list) -> dict:
    """Recalcule les statistiques à partir des visites."""
    stats = {
        "visits": len(visits),
        "unique_visitors": len({v["visitor_id"] for v in visits}),
        "unique_ips": len({v["ip"] for v in visits}),
        "premium_clicks": 0,
        "unique_premium_visitors": set(),
        "emails": 0,
        "don_clicks": 0,
        "unique_don_ips": set(),
        "audio_clicks": 0,
        "deals": 0,
        "web_visits": 0,
        "android_visits": 0,
        "reveals": 0,
        "interprets": 0,
        "chats": 0,
        "exports": 0,
        "errors": 0,
        "event_types": Counter(),
    }
    for v in visits:
        ip = v["ip"]
        visitor = v["visitor_id"]
        source = visit_source(v)
        if source == "android":
            stats["android_visits"] += 1
        else:
            stats["web_visits"] += 1
        has_premium = False
        for e in v.get("events", []):
            etype = e["type"]
            stats["event_types"][etype] += 1
            if etype == "premium_click":
                stats["premium_clicks"] += 1
                has_premium = True
            elif etype == "don_click":
                stats["don_clicks"] += 1
                stats["unique_don_ips"].add(ip)
            elif etype == "premium_email":
                stats["emails"] += 1
            elif etype == "audio_click":
                stats["audio_clicks"] += 1
            elif etype == "deal":
                stats["deals"] += 1
            elif etype == "reveal":
                stats["reveals"] += 1
            elif etype == "interpret":
                stats["interprets"] += 1
            elif etype == "chat":
                stats["chats"] += 1
            elif etype == "export":
                stats["exports"] += 1
            elif etype in {"error", "interpret_fail"}:
                stats["errors"] += 1
        if has_premium:
            stats["unique_premium_visitors"].add(visitor)
    stats["unique_premium_visitors"] = len(stats["unique_premium_visitors"])
    stats["unique_don_ips"] = len(stats["unique_don_ips"])
    return stats


def visit_source(visit: dict) -> str:
    source = (visit.get("source") or "").strip().lower()
    return source if source in {"web", "android"} else "web"


def event_extra_label(event: dict) -> str:
    bits = []
    if event.get("type") == "premium_email" and event.get("email"):
        bits.append(f"email: {event['email']}")
    if event.get("type") == "reveal" and event.get("n") is not None:
        bits.append(f"carte {event['n']}/3")
    if event.get("type") == "error" and event.get("code"):
        bits.append(event["code"])
    if event.get("type") == "interpret_fail" and event.get("code"):
        bits.append(event["code"])
    return f" ({', '.join(bits)})" if bits else ""

# ----------------------------------------------------------------------
# Génération de la page HTML
# ----------------------------------------------------------------------
def generate_dashboard_html(data: dict, updated_at: str) -> str:
    visits = data.get("visits", [])
    visits_sorted = sorted(visits, key=lambda v: parse_ts(v["started_at"]), reverse=True)
    stats = recalc_stats(visits)

    # Collecte des emails
    emails = []
    for v in visits:
        email = get_email_from_visit(v)
        if email:
            emails.append({
                "email": email,
                "visitor_id": v["visitor_id"],
                "ip": v["ip"],
                "date": v["started_at"]
            })

    # Construction du HTML
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tableau de bord - Logs prospects</title>
    <style>
        :root {{
            --bg: #f8f9fa;
            --card-bg: #ffffff;
            --text: #212529;
            --muted: #6c757d;
            --border: #dee2e6;
            --primary: #0d6efd;
            --success: #198754;
            --warning: #ffc107;
            --danger: #dc3545;
            --info: #0dcaf0;
            --dark: #212529;
            --shadow: 0 0.5rem 1rem rgba(0,0,0,0.05);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 1.5rem;
            line-height: 1.5;
        }}
        h1 {{ font-size: 1.8rem; font-weight: 600; margin-bottom: 1rem; }}
        h2 {{ font-size: 1.4rem; font-weight: 500; margin: 1.5rem 0 0.8rem; }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }}
        .header .updated {{ color: var(--muted); font-size: 0.9rem; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            padding: 1rem;
            text-align: center;
            box-shadow: var(--shadow);
        }}
        .stat-value {{ font-size: 1.8rem; font-weight: 700; color: var(--primary); }}
        .stat-label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }}
        .search-box {{
            margin: 1rem 0;
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        .search-box input {{
            padding: 0.5rem 0.75rem;
            border: 1px solid var(--border);
            border-radius: 0.375rem;
            flex: 1;
            min-width: 200px;
            font-size: 0.95rem;
        }}
        .search-box button {{
            padding: 0.5rem 1rem;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 0.375rem;
            cursor: pointer;
            font-size: 0.95rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border-radius: 0.5rem;
            overflow: hidden;
            box-shadow: var(--shadow);
            margin-bottom: 2rem;
        }}
        th, td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background: var(--dark);
            color: white;
            font-weight: 500;
            font-size: 0.9rem;
        }}
        tr:hover {{ background-color: rgba(0,0,0,0.02); }}
        .visit-row {{ cursor: pointer; }}
        .events-detail {{
            display: none;
            background: #f1f3f5;
            padding: 1rem;
            margin: 0;
        }}
        .events-detail td {{ border-bottom: none; }}
        .event-item {{
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 0.85rem;
            padding: 0.25rem 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .event-type {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            color: white;
            min-width: 90px;
            text-align: center;
        }}
        .premium_click {{ background: var(--primary); }}
        .don_click {{ background: var(--success); }}
        .premium_email {{ background: var(--warning); color: var(--dark); }}
        .visit_start {{ background: var(--info); }}
        .deal {{ background: var(--danger); }}
        .audio_click {{ background: #6f42c1; }}
        .reveal {{ background: #fd7e14; }}
        .interpret {{ background: #20c997; }}
        .interpret_fail {{ background: var(--danger); }}
        .chat {{ background: #6610f2; }}
        .export {{ background: #0b7285; }}
        .error {{ background: #495057; }}
        .source-pill {{
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .source-web {{ background: #e7f1ff; color: #0b5ed7; }}
        .source-android {{ background: #d3f9d8; color: #2b8a3e; }}
        .filter-bar {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.5rem 0 1rem; }}
        .filter-bar button {{
            padding: 0.4rem 0.8rem;
            border: 1px solid var(--border);
            background: white;
            border-radius: 999px;
            cursor: pointer;
            font-size: 0.85rem;
        }}
        .filter-bar button.active {{ background: var(--dark); color: white; border-color: var(--dark); }}
        .version {{ color: var(--muted); font-size: 0.75rem; }}
        .email-list {{
            list-style: none;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            padding: 1rem;
            box-shadow: var(--shadow);
        }}
        .email-list li {{
            padding: 0.5rem 0;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
        }}
        .email-list li:last-child {{ border-bottom: none; }}
        .muted {{ color: var(--muted); font-size: 0.85rem; }}
        .btn-logout {{
            background: none;
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.4rem 0.8rem;
            border-radius: 0.375rem;
            cursor: pointer;
            font-size: 0.9rem;
            text-decoration: none;
            display: inline-block;
        }}
        .btn-logout:hover {{ background: #e9ecef; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Tableau de bord des logs prospects</h1>
        <div style="display: flex; gap: 0.5rem;">
            <button onclick="location.reload()" class="btn-logout">🔄 Rafraîchir</button>
            <a href="/logs/export.md" class="btn-logout" target="_blank">📄 Exporter MD</a>
            <a href="/logs/logout" class="btn-logout">Déconnexion</a>
        </div>
    </div>
    <p class="updated">Dernière mise à jour : {updated_at}</p>

    <div class="stats-grid">
        <div class="stat-card"><div class="stat-value">{stats['visits']}</div><div class="stat-label">Visites</div></div>
        <div class="stat-card"><div class="stat-value">{stats['web_visits']}</div><div class="stat-label">Web</div></div>
        <div class="stat-card"><div class="stat-value">{stats['android_visits']}</div><div class="stat-label">Android</div></div>
        <div class="stat-card"><div class="stat-value">{stats['unique_visitors']}</div><div class="stat-label">Visiteurs uniques</div></div>
        <div class="stat-card"><div class="stat-value">{stats['unique_ips']}</div><div class="stat-label">IP uniques</div></div>
        <div class="stat-card"><div class="stat-value">{stats['deals']}</div><div class="stat-label">Deals</div></div>
        <div class="stat-card"><div class="stat-value">{stats['reveals']}</div><div class="stat-label">Révélations</div></div>
        <div class="stat-card"><div class="stat-value">{stats['interprets']}</div><div class="stat-label">Interprétations</div></div>
        <div class="stat-card"><div class="stat-value">{stats['chats']}</div><div class="stat-label">Messages</div></div>
        <div class="stat-card"><div class="stat-value">{stats['exports']}</div><div class="stat-label">Exports</div></div>
        <div class="stat-card"><div class="stat-value">{stats['premium_clicks']}</div><div class="stat-label">Clics Premium</div></div>
        <div class="stat-card"><div class="stat-value">{stats['emails']}</div><div class="stat-label">Emails</div></div>
        <div class="stat-card"><div class="stat-value">{stats['don_clicks']}</div><div class="stat-label">Clics Don</div></div>
        <div class="stat-card"><div class="stat-value">{stats['audio_clicks']}</div><div class="stat-label">Clics Audio</div></div>
        <div class="stat-card"><div class="stat-value">{stats['errors']}</div><div class="stat-label">Erreurs</div></div>
    </div>

    <h2>🔍 Filtre</h2>
    <div class="filter-bar" id="sourceFilter">
        <button type="button" class="active" data-source="all">Tous</button>
        <button type="button" data-source="web">Web</button>
        <button type="button" data-source="android">Android</button>
    </div>
    <div class="search-box">
        <input type="text" id="searchInput" placeholder="Recherche par IP, visiteur, source, type d'événement...">
        <button onclick="resetFilter()">Réinitialiser</button>
    </div>

    <h2>📋 Visites ({stats['visits']} au total — {stats['web_visits']} web · {stats['android_visits']} Android)</h2>
    <table id="visitsTable">
        <thead>
            <tr>
                <th>Date</th>
                <th>Source</th>
                <th>IP</th>
                <th>Visiteur</th>
                <th>Durée</th>
                <th>Événements</th>
                <th>Types</th>
                <th>Email</th>
            </tr>
        </thead>
        <tbody>
    """

    for visit in visits_sorted:
        events = sort_events(visit.get("events", []))
        duration = get_visit_duration(visit)
        event_types = [e["type"] for e in events]
        types_display = ", ".join(sorted(set(event_types)))
        email = get_email_from_visit(visit) or ""
        source = visit_source(visit)
        version = visit.get("app_version") or ""
        locale = visit.get("locale") or ""
        version_html = f'<div class="version">{version} {locale}</div>' if version or locale else ""
        data_search = f"{visit['ip']} {visit['visitor_id']} {source} {version} {locale} {' '.join(event_types)}"

        html += f"""
            <tr class="visit-row" data-search="{data_search}" data-source="{source}">
                <td>{visit['started_at'][:19].replace('T', ' ')}</td>
                <td><span class="source-pill source-{source}">{source}</span>{version_html}</td>
                <td>{visit['ip']}</td>
                <td title="{visit['visitor_id']}">{visit['visitor_id'][:12]}…</td>
                <td>{duration}s</td>
                <td>{len(events)}</td>
                <td>{types_display}</td>
                <td>{email}</td>
            </tr>
            <tr class="events-detail" id="detail-{visit['visit_id']}">
                <td colspan="8">
                    <strong>Timeline des événements :</strong>
                    <div style="margin-top:0.5rem;">
        """
        for e in events:
            etype = e["type"]
            extra = event_extra_label(e)
            html += f"""<div class="event-item"><span class="event-type {etype}">{etype}</span>{e['ts'][:19].replace('T', ' ')}{extra}</div>\n"""
        html += """</div></td></tr>"""

    html += """</tbody></table>

    <h2>📧 Emails collectés ({emails_count})</h2>
    <ul class="email-list">
    """.format(emails_count=len(emails))

    if emails:
        for em in emails:
            html += f"<li><span>{em['email']}</span><span class='muted'>(visiteur {em['visitor_id'][:12]}…, IP {em['ip']}, le {em['date'][:19].replace('T', ' ')})</span></li>\n"
    else:
        html += "<li>Aucun email collecté.</li>\n"

    html += """</ul>

    <script>
        const searchInput = document.getElementById('searchInput');
        let sourceFilter = 'all';
        function applyFilters() {
            const filter = searchInput.value.toLowerCase();
            const rows = document.querySelectorAll('#visitsTable tbody tr.visit-row');
            rows.forEach(row => {
                const searchData = (row.getAttribute('data-search') || '').toLowerCase();
                const source = row.getAttribute('data-source') || 'web';
                const sourceOk = sourceFilter === 'all' || source === sourceFilter;
                const textOk = !filter || searchData.includes(filter);
                row.style.display = sourceOk && textOk ? '' : 'none';
                const detailRow = row.nextElementSibling;
                if (detailRow && detailRow.classList.contains('events-detail')) {
                    detailRow.style.display = 'none';
                }
            });
        }
        searchInput.addEventListener('input', applyFilters);
        document.querySelectorAll('#sourceFilter button').forEach(button => {
            button.addEventListener('click', function() {
                sourceFilter = this.getAttribute('data-source') || 'all';
                document.querySelectorAll('#sourceFilter button').forEach(item => item.classList.remove('active'));
                this.classList.add('active');
                applyFilters();
            });
        });
        function resetFilter() {
            searchInput.value = '';
            sourceFilter = 'all';
            document.querySelectorAll('#sourceFilter button').forEach(item => {
                item.classList.toggle('active', item.getAttribute('data-source') === 'all');
            });
            applyFilters();
        }
        document.querySelectorAll('.visit-row').forEach(row => {
            row.addEventListener('click', function() {
                const detailRow = this.nextElementSibling;
                if (detailRow && detailRow.classList.contains('events-detail')) {
                    detailRow.style.display = detailRow.style.display === 'none' ? 'table-row' : 'none';
                }
            });
        });
    </script>
</body>
</html>"""
    return html

# ----------------------------------------------------------------------
# Génération du Markdown
# ----------------------------------------------------------------------
def generate_markdown(data: dict, updated_at: str) -> str:
    visits = data.get("visits", [])
    visits_sorted = sorted(visits, key=lambda v: parse_ts(v["started_at"]), reverse=True)
    stats = recalc_stats(visits)

    # Collecte des emails
    emails = []
    for v in visits:
        email = get_email_from_visit(v)
        if email:
            emails.append({
                "email": email,
                "visitor_id": v["visitor_id"],
                "ip": v["ip"],
                "date": v["started_at"]
            })

    lines = []
    lines.append("# Rapport des logs prospects\n")
    lines.append(f"**Dernière mise à jour** : {updated_at}\n")
    lines.append("## Statistiques globales\n")
    lines.append("| Métrique | Valeur |")
    lines.append("|----------|--------|")
    lines.append(f"| Visites | {stats['visits']} |")
    lines.append(f"| Visiteurs uniques | {stats['unique_visitors']} |")
    lines.append(f"| IP uniques | {stats['unique_ips']} |")
    lines.append(f"| Clics Premium | {stats['premium_clicks']} |")
    lines.append(f"| Visiteurs Premium | {stats['unique_premium_visitors']} |")
    lines.append(f"| Emails | {stats['emails']} |")
    lines.append(f"| Clics Don | {stats['don_clicks']} |")
    lines.append(f"| IPs Don uniques | {stats['unique_don_ips']} |")
    lines.append(f"| Clics Audio | {stats['audio_clicks']} |")
    lines.append(f"| Deals | {stats['deals']} |\n")

    lines.append("## Visites détaillées\n")
    for visit in visits_sorted:
        events = sort_events(visit.get("events", []))
        duration = get_visit_duration(visit)
        email = get_email_from_visit(visit)
        started = visit['started_at'][:19].replace('T', ' ')
        lines.append(f"### Visite du {started} - IP {visit['ip']}\n")
        lines.append(f"- **Visiteur** : {visit['visitor_id']}")
        lines.append(f"- **Début** : {started}")
        lines.append(f"- **Durée** : {duration}s")
        if email:
            lines.append(f"- **Email** : {email}")
        lines.append(f"- **Session ID** : {visit['session_id']}")
        lines.append("- **Événements** :")
        for i, e in enumerate(events, 1):
            etype = e["type"]
            ts = e['ts'][:19].replace('T', ' ')
            email_info = f" (email: {e.get('email', '')})" if etype == "premium_email" else ""
            lines.append(f"  {i}. `{etype}` à {ts}{email_info}")
        lines.append("")

    lines.append("## Emails collectés\n")
    if emails:
        for em in emails:
            lines.append(f"- {em['email']} (visiteur {em['visitor_id']}, IP {em['ip']}, le {em['date'][:19].replace('T', ' ')})")
    else:
        lines.append("- Aucun email collecté.")

    return "\n".join(lines)

# ----------------------------------------------------------------------
# Génération de la page de connexion
# ----------------------------------------------------------------------
def generate_login_html(error: Optional[str] = None) -> str:
    error_msg = f"<p style='color:red;'>{error}</p>" if error else ""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connexion - Logs</title>
    <style>
        body {{
            font-family: system-ui, sans-serif;
            background: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }}
        .login-box {{
            background: white;
            padding: 2rem;
            border-radius: 0.5rem;
            box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }}
        h1 {{ font-size: 1.5rem; margin-bottom: 1rem; text-align: center; }}
        input[type="password"] {{
            width: 100%;
            padding: 0.75rem;
            margin-bottom: 1rem;
            border: 1px solid #ddd;
            border-radius: 0.375rem;
            font-size: 1rem;
        }}
        button {{
            width: 100%;
            padding: 0.75rem;
            background: #0d6efd;
            color: white;
            border: none;
            border-radius: 0.375rem;
            font-size: 1rem;
            cursor: pointer;
        }}
        button:hover {{ background: #0b5ed7; }}
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🔐 Accès aux logs</h1>
        {error_msg}
        <form method="post" action="/logs/login">
            <input type="password" name="code" placeholder="Code d'accès" required autofocus>
            <button type="submit">Se connecter</button>
        </form>
    </div>
</body>
</html>"""

# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Affiche le formulaire de connexion."""
    if get_current_auth(request):
        return RedirectResponse(url="/logs")
    return generate_login_html()

@router.post("/login")
async def login_submit(request: Request):
    """Vérifie le code et crée la session."""
    form = await request.form()
    code = form.get("code", "")
    if code == LOG_ACCESS_CODE:
        token = create_session_token()
        response = RedirectResponse(url="/logs", status_code=303)
        response.set_cookie(SESSION_COOKIE_NAME, token, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax")
        return response
    else:
        return generate_login_html(error="Code incorrect.")

@router.get("/logout")
async def logout():
    """Supprime le cookie de session."""
    response = RedirectResponse(url="/logs/login")
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response

@router.get("/export.md", response_class=PlainTextResponse)
async def export_markdown(request: Request):
    """Exporte les logs au format Markdown (protégé)."""
    if not get_current_auth(request):
        return RedirectResponse(url="/logs/login")
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        updated_at = data.get("updated_at", "inconnu")
        md = generate_markdown(data, updated_at)
        return PlainTextResponse(content=md, media_type="text/markdown")
    except FileNotFoundError:
        return PlainTextResponse(content=f"Fichier de logs introuvable : {LOG_FILE}", status_code=500)
    except json.JSONDecodeError as e:
        return PlainTextResponse(content=f"Erreur de parsing JSON : {e}", status_code=500)

@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Affiche le tableau de bord (protégé)."""
    if not get_current_auth(request):
        return RedirectResponse(url="/logs/login")
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        updated_at = data.get("updated_at", "inconnu")
        html = generate_dashboard_html(data, updated_at)
        return HTMLResponse(content=html)
    except FileNotFoundError:
        return HTMLResponse(content=f"<h1>Fichier de logs introuvable</h1><p>{LOG_FILE}</p>", status_code=500)
    except json.JSONDecodeError as e:
        return HTMLResponse(content=f"<h1>Erreur de parsing JSON</h1><p>{e}</p>", status_code=500)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(content=f"<h1>Erreur interne</h1><p>{str(e)}</p>", status_code=500)
