# Collab Portal — TAIG & Associates

Simple team idea-sharing board for the TAIG team — especially the artists — to
share ideas and plan together. Phone-friendly, open for now, no login friction
in v1.

- **Base:** [Planka](https://github.com/plankanban/planka) Community edition
  v2.3.1, self-hosted Kanban (boards, lists, cards, comments, markdown,
  real-time updates). Pinned version, not `latest`.
- **Live:** http://138.68.226.24/collab-portal/
- **Host:** Droplet #1 (138.68.226.24), SSH build, Nebula style.
  GitHub-first, Droplet pull-only: the Droplet clones/pulls this repo and
  runs `deploy.sh`. No direct edits on the Droplet.
- **Route:** Nginx on the Droplet proxies `/collab-portal/` to Planka on
  loopback `127.0.0.1:3003`. Planka is never exposed on a public port.
  Only ports 22 + 80 stay open.

## License note

Planka is **Fair Use / fair-code**, NOT MIT: source-available, free to
self-host and customize for the team. Check the license before any
commercial use or resale. See `LICENSE.md` in the Planka repo.

## v1 scope

- Planka as-is + TAIG flair (project/board naming, seeded team board).
- One seeded ideas board: **Team Ideas** — Ideas / Planning / Doing / Done.
- Placeholder accounts only. No real emails or passwords are invented or
  committed. Account credentials live on the Droplet only, in
  `/opt/collab-portal/PLACEHOLDER_ACCOUNTS.md` (chmod 600, not in git).
  Tee hands them out / replaces them.

## Out of scope for v1 (future build)

- MySpace-style profiles / personal pages — Tee's future direction, not v1.
- No login/SSO system beyond Planka's built-in accounts.
- No external outreach, no messages to the team, no spending.

## Deploy (on the Droplet)

```bash
cd /opt/collab-portal
git pull
cp .env.example .env   # first time only, then fill in real secrets
./deploy.sh
```

`deploy.sh` creates the `collab-portal-net` network and the two volumes,
runs Postgres 16 + Planka 2.3.1 as `--restart unless-stopped` containers,
and waits for Planka to answer on loopback. It never wipes the database
volumes on re-run.

Nginx: the snippet in `nginx/collab-portal.conf` goes inside the `nope`
vhost (`/etc/nginx/sites-enabled/nope`), before `location /`. Then
`nginx -t && systemctl reload nginx`.

## Seed

After first deploy, from the Droplet:

```bash
cd /opt/collab-portal
./seed/seed.py   # reads /opt/collab-portal/.env, creates users + board
```

Seed creates the placeholder team users (Andrea, Star girl, Ethan, Jay,
Josh), the project "Collab Portal — TAIG & Associates", the "Team Ideas"
board, the four lists, and a few starter idea cards. It prints the
generated placeholder passwords to stdout — save them to
`PLACEHOLDER_ACCOUNTS.md` on the Droplet, never to git.

## Repo layout

- `docker-compose.yml` — canonical compose file (dev / reference; the
  Droplet runs plain `docker run` via `deploy.sh` because the Droplet has
  no compose plugin installed).
- `deploy.sh` — Droplet deploy script.
- `nginx/collab-portal.conf` — Nginx location snippet.
- `seed/seed.py` — API seeding script (stdlib only).
- `.env.example` — placeholder env vars, no real secrets.
