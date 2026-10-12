# Daily AI Notes

AI takes notes on what's happening, every day, on the things you care about.

Every day, LangGraph agents collect coverage for each topic in a fixed catalog, cluster duplicate reports into stories, research them, write short notes with inline citations, fact-check every claim and wait for a human approval before publishing. Visitors read the notes for the topics they pick and ask questions answered only from the notes, with citations.

**Status:** proof of concept, under construction ([ADR 0001](docs/adr/0001-proof-of-concept-scope.md)). The milestones are listed in [INTENT.md](INTENT.md).

## Development

Requires [uv](https://docs.astral.sh/uv/), Python 3.14 and Docker.

```sh
uv sync
cp .env.example .env
uv run pre-commit install
make up      # Postgres 18 with pgvector, in Docker
make check   # format, lint, types, tests (integration tests need `make up`)
make api     # the API on http://localhost:8000; try /api/v1/health
```

## Running the pipeline

```sh
uv run dan catalog sync              # load config/catalog.toml
uv run dan topics plan --all         # the Topic Planner proposes sources for each draft topic
uv run dan review list               # approve or reject: dan review approve plan-<id>
uv run dan edition run --all         # today's notes; each waits for dan review approve note-<id>
```

The model steps need `OLLAMA_API_KEY` or `OPENROUTER_API_KEY` in `.env`; `uv run dan llm probe` shows which models answer.

## Deploy

One VPS (Ubuntu 24.04, x86_64; 2 vCPU and 4 GB of memory are enough) runs everything with Docker Compose: Caddy, the API, the worker and Postgres. Each merge to `main` that passes CI builds the image, pushes it to GHCR and runs [`deploy/deploy.sh`](deploy/deploy.sh) on the server over SSH. That script pulls the image, migrates the database, starts the stack, checks `/api/v1/health` over HTTPS, and redeploys the previous image if any step fails.

### Server setup, once

As root on a fresh server:

```sh
# Docker Engine and Compose, from Docker's apt repository (docs.docker.com/engine/install/ubuntu)
apt update && apt install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt update && apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Security updates install themselves
apt install -y unattended-upgrades && dpkg-reconfigure -f noninteractive unattended-upgrades

# Firewall: SSH, HTTP and HTTPS (443/udp for HTTP/3). Only Caddy publishes ports.
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw allow 443/udp && ufw enable

# The deploy user and the app folder. Membership of the docker group is root-equivalent:
# guard this user's keys.
adduser --disabled-password --gecos "" deploy && usermod -aG docker deploy
install -d -o deploy -g deploy -m 700 /srv/dailyainotes
install -d -o deploy -g deploy -m 700 /home/deploy/.ssh
# Put your public key and the deploy workflow's public key in /home/deploy/.ssh/authorized_keys.

# SSH: keys only, no root login
tee /etc/ssh/sshd_config.d/10-hardening.conf <<EOF
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
EOF
systemctl reload ssh
```

Then, as `deploy`, write `/srv/dailyainotes/.env` (mode 600). It takes every setting in [`.env.example`](.env.example) except `DATABASE_URL`, which Compose builds, plus:

```sh
IMAGE=ghcr.io/<owner>/dailyainotes   # lower case
DOMAIN=dailyainotes.com
POSTGRES_PASSWORD=                   # openssl rand -hex 32
```

Point the domain's A record (and AAAA, if the server has IPv6) at the server; Caddy obtains the certificate on the first request.

### GitHub settings

- Variable `DEPLOY_HOST`: the server's address. Until it is set, CI builds and pushes images but does not deploy.
- Secret `DEPLOY_SSH_KEY`: a private key made only for deploys (`ssh-keygen -t ed25519 -f deploy_key -N ""`), whose public half is in `deploy`'s `authorized_keys`.
- Secret `DEPLOY_KNOWN_HOSTS`: the output of `ssh-keyscan -t ed25519 <server>`.
- After the first push, make the `dailyainotes` package public in its GHCR settings, so the server pulls without a token. Otherwise, run `docker login ghcr.io` as `deploy` with a token that can only read packages.

### First run on the server

Commands run in the worker's container, which has the most memory. In `/srv/dailyainotes`:

```sh
alias dan='TAG=$(cat .deployed) docker compose -f compose.prod.yml exec worker dan'
dan catalog sync
dan topics plan --all && dan review list
```

The worker runs every active topic's edition at 01:30 UTC; `dan review list` shows the notes waiting for approval.

### Backups

`backup.sh` dumps the database into `backups/` and keeps the newest 7. Schedule it with `crontab -e` as `deploy`:

```cron
30 0 * * * /srv/dailyainotes/backup.sh >> /srv/dailyainotes/backups/backup.log 2>&1
```

`./restore-check.sh` restores the newest dump into a scratch database, prints what it holds and drops it; run it after the first backup and now and then. To restore the live database from a dump:

```sh
export TAG=$(cat .deployed)
docker compose -f compose.prod.yml stop api worker
docker compose -f compose.prod.yml exec -T db dropdb -U dan dailyainotes
docker compose -f compose.prod.yml exec -T db createdb -U dan dailyainotes
docker compose -f compose.prod.yml exec -T db pg_restore -U dan -d dailyainotes --no-owner < backups/<file>.dump
docker compose -f compose.prod.yml start api worker
```

To go back to an earlier release, run `./deploy.sh <commit sha>`. Logs: `TAG=$(cat .deployed) docker compose -f compose.prod.yml logs -f worker`.

## How this repository is run

- [AGENTS.md](AGENTS.md): how humans and coding agents work here
- [INTENT.md](INTENT.md): rules and standing tasks
- [MEMORY.md](MEMORY.md): what has been learned, with sources
- [DESIGN.md](DESIGN.md): the visual system

## License

[Apache-2.0](LICENSE)
