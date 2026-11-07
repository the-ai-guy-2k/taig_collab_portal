# Collab Portal — TAIG & Associates

Simple team idea-sharing board for the TAIG team — especially the artists — to
share ideas and plan together. Phone-friendly, open for now, no login friction
in v1.

- **Base:** [Planka](https://github.com/plankanban/planka) Community edition
  v2.3.1, self-hosted Kanban (boards, lists, cards, comments, markdown,
  real-time updates). Pinned version, not `latest`.
- **Live:** https://taigtsp.duckdns.org/collab-portal/ (HTTPS, Let's Encrypt)
- **Host:** Droplet #1 (138.68.226.24), SSH build, Nebula style.
  GitHub-first, Droplet pull-only: the Droplet clones/pulls this repo and
  runs `deploy.sh`. No direct edits on the Droplet.
- **Route:** Nginx on the Droplet proxies `/collab-portal/` to Planka on
  loopback `127.0.0.1:3003`. Planka is never exposed on a public port.
  The portal lives on the `taigtsp.duckdns.org` vhost: HTTP requests to
  `/collab-portal/` 301-redirect to the HTTPS URL, and the old IP URL
  (`http://138.68.226.24/collab-portal/`) redirects there too.
  Ports 22 + 80 + 443 stay open; 443 was never blocked (INPUT only drops
  the container ports). Cert: free Let's Encrypt for taigtsp.duckdns.org,
  auto-renewal on (certbot timer), registered without an email address.
  The same cert also covers TSP, Jay EPK, resumes, AI Workforce, and the
  operator services (Business Dashboard, PIA, DIME, VA benefits, stadium
  time-lapse, EPK analytics, Andrea onboarding) on that name — except
  Nope itself, which needs its own domain name (root-relative links, can't
  live under a subpath) and is still HTTP-only on the IP for now.

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

Nginx: the snippet in `nginx/collab-portal.conf` goes inside the `taigtsp`
vhost (`/etc/nginx/sites-enabled/taigtsp`), in the 443 server block, before
`location /`. The port-80 block 301-redirects `/collab-portal/` to the
HTTPS URL. Then `nginx -t && systemctl reload nginx`. (The snippet was
first added to the IP `nope` vhost on Nov 7; it moved to `taigtsp` when
HTTPS went live the same evening. The `nope` vhost now only 301-redirects
the old IP URL to HTTPS.)

## Admin password

Planka's default admin (`tee@collab-portal.local`) is protected from
password changes through the API. If the admin password is ever lost,
reset it with Planka's own seed: set `DEFAULT_ADMIN_PASSWORD` in the
Droplet `.env` to the new password and re-run `./deploy.sh` — the seed
runs on container start and updates the admin user's password. (This is
how the Nov 7 login fault was fixed: the password reported in the build
report did not match the account, and the fix was a re-seed to a
word-based passphrase, verified by a real HTTPS login.)

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
