#!/usr/bin/env python3
"""Seed the Collab Portal (Planka) via its REST API. Stdlib only.

Reads /opt/collab-portal/.env for the admin login (DEFAULT_ADMIN_USERNAME /
DEFAULT_ADMIN_PASSWORD). Talks to Planka on loopback (default
http://127.0.0.1:3003) so seeding does not depend on Nginx.

Creates, if they do not already exist:
  - placeholder team users (Andrea, Star girl, Ethan, Jay, Josh)
  - project "Collab Portal — TAIG & Associates" (shared)
  - board "Team Ideas" with lists Ideas / Planning / Doing / Done
  - starter idea cards (labelled as seeds, no fake plans or commitments)
  - board memberships (editor) for every team user

Prints generated placeholder passwords to stdout. Save them to
/opt/collab-portal/PLACEHOLDER_ACCOUNTS.md on the Droplet — never to git.
"""
import json
import os
import secrets
import sys
import urllib.request
import urllib.error

BASE = os.environ.get("PLANKA_URL", "http://127.0.0.1:3003")
ENV_FILE = os.environ.get("ENV_FILE", "/opt/collab-portal/.env")


def load_env(path):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env


def req(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {detail[:500]}")


def login(admin_user, admin_pass):
    """Log in, accepting Planka's first-run terms if the instance asks.

    Planka 2.3 requires the default terms to be accepted on first login:
    POST /api/access-tokens returns 403 with a pendingToken, then
    POST /api/access-tokens/accept-terms with that token plus the SHA256
    signature from GET /api/terms completes the login.
    """
    try:
        resp = req("POST", "/api/access-tokens",
                   body={"emailOrUsername": admin_user, "password": admin_pass})
        item = resp["item"]
        return item["accessToken"] if isinstance(item, dict) else item
    except RuntimeError as e:
        if "accept-terms" not in str(e):
            raise
        import re
        m = re.search(r'"pendingToken":"([^"]+)"', str(e))
        if not m:
            raise RuntimeError(f"accept-terms step but no pendingToken in: {e}")
        pending = m.group(1)
        terms = req("GET", "/api/terms")
        done = req("POST", "/api/access-tokens/accept-terms",
                   body={"pendingToken": pending, "signature": terms["signature"]})
        item = done["item"]
        print("Accepted Planka default terms on first admin login.")
        return item["accessToken"] if isinstance(item, dict) else item


def main():
    env = load_env(ENV_FILE)
    admin_user = env.get("DEFAULT_ADMIN_USERNAME", "tee")
    admin_pass = env.get("DEFAULT_ADMIN_PASSWORD")
    if not admin_pass or admin_pass.startswith("CHANGE_ME"):
        print("ERROR: set a real DEFAULT_ADMIN_PASSWORD in .env first.", file=sys.stderr)
        return 1

    token = login(admin_user, admin_pass)
    print("Logged in as admin.")

    users = req("GET", "/api/users", token)["items"]
    by_username = {u.get("username"): u for u in users}

    team = [
        ("Andrea", "andrea", "Andrea"),
        ("Star girl", "stargirl", "Star girl"),
        ("Ethan", "ethan", "Ethan"),
        ("Jay Garrett", "jay", "Jay Garrett"),
        ("Josh Stephenson", "josh", "Josh Stephenson"),
    ]
    passwords = {}
    user_ids = {}
    for name, username, _label in team:
        if username in by_username:
            user_ids[username] = by_username[username]["id"]
            print(f"User {username} already exists, reusing.")
            continue
        pw = secrets.token_urlsafe(12)
        created = req("POST", "/api/users", token, body={
            "email": f"{username}@collab-portal.local",
            "password": pw, "role": "boardUser",
            "name": name, "username": username,
        })
        user_ids[username] = created["item"]["id"]
        passwords[username] = pw
        print(f"Created user {username} ({name}).")

    projects = req("GET", "/api/projects", token)["items"]
    project = next((p for p in projects
                    if p["name"] == "Collab Portal — TAIG & Associates"), None)
    if project:
        project_id = project["id"]
        print("Project already exists, reusing.")
    else:
        project = req("POST", "/api/projects", token, body={
            "type": "shared",
            "name": "Collab Portal — TAIG & Associates",
            "description": "TAIG & Associates team board. Ideas and planning for the whole team — artists first. MySpace-style profiles are a future build, not v1.",
        })
        project_id = project["item"]["id"]
        print("Created project.")

    detail = req("GET", f"/api/projects/{project_id}", token)
    boards = detail.get("included", {}).get("boards", [])
    board = next((b for b in boards if b["name"] == "Team Ideas"), None)
    if board:
        board_id = board["id"]
        print("Board already exists, reusing.")
    else:
        board = req("POST", f"/api/projects/{project_id}/boards", token,
                    body={"position": 65536, "name": "Team Ideas"})
        board_id = board["item"]["id"]
        print("Created board 'Team Ideas'.")

    board_detail = req("GET", f"/api/boards/{board_id}", token)
    lists = board_detail.get("included", {}).get("lists", [])
    list_by_name = {l["name"]: l for l in lists}
    list_defs = [("Ideas", "active"), ("Planning", "active"),
                 ("Doing", "active"), ("Done", "closed")]
    list_ids = {}
    for i, (lname, ltype) in enumerate(list_defs):
        if lname in list_by_name:
            list_ids[lname] = list_by_name[lname]["id"]
            continue
        created = req("POST", f"/api/boards/{board_id}/lists", token, body={
            "type": ltype, "position": 65536 * (i + 1), "name": lname,
        })
        list_ids[lname] = created["item"]["id"]
        print(f"Created list {lname}.")

    existing_cards = set()
    for lname, lid in list_ids.items():
        for c in req("GET", f"/api/lists/{lid}/cards", token)["items"]:
            existing_cards.add(c["name"])

    cards = [
        ("Ideas", "Welcome to the Collab Portal",
         "This is where the TAIG team shares ideas and plans together — artists first. Drop an idea as a card, move it across as it turns into a plan. MySpace-style profiles / personal pages are a future build, not v1."),
        ("Ideas", "Jay — 'Still Chasing the Sunset' promo ideas",
         "Jay Garrett, recording artist. Album 'Still Chasing the Sunset' out Oct 19, 2026. Ideas for promo, gigs, flyers — Ethan on design, Star girl on the look."),
        ("Ideas", "Josh — Welcome to Rockville run",
         "Josh Stephenson, heavy-metal artist, working toward Welcome to Rockville (May 6–9, 2027). Ideas for the run, the set, and the promo around it."),
        ("Ideas", "Ethan — flyer ideas for Jay & Josh",
         "Ethan runs @beforewemetflyers (flyers, merch, logos, photo edits). Flyer and art ideas for both artists go here."),
        ("Planning", "Andrea — first sales targets",
         "Andrea runs Sales for TAIG ITS. First targets and talk tracks to agree as a team — nothing here is a promise to anyone yet."),
        ("Planning", "Star girl — Associates: non-AI promo ideas",
         "Star girl runs the Associates division — anything non-AI, promotion-related. Promo ideas that are human, no AI, go here."),
    ]
    for i, (lname, name, desc) in enumerate(cards):
        if name in existing_cards:
            print(f"Card already exists, skipping: {name}")
            continue
        req("POST", f"/api/lists/{list_ids[lname]}/cards", token, body={
            "type": "project", "position": 65536 * (i + 1),
            "name": name, "description": desc,
        })
        print(f"Created card: {name}")

    for username, uid in user_ids.items():
        try:
            req("POST", f"/api/boards/{board_id}/board-memberships", token,
                body={"userId": uid, "role": "editor", "canComment": True})
            print(f"Added {username} to the board as editor.")
        except RuntimeError as e:
            print(f"Note: could not add {username} to board (may already be a member): {e}")

    print("\n=== PLACEHOLDER ACCOUNTS (save to PLACEHOLDER_ACCOUNTS.md, never to git) ===")
    print(f"Admin: username {admin_user} (password is in .env)")
    for username, pw in passwords.items():
        print(f"{username}: password {pw}  (email {username}@collab-portal.local)")
    print("=== END ===")
    print(f"\nLive at: {env.get('BASE_URL', 'http://138.68.226.24/collab-portal')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
