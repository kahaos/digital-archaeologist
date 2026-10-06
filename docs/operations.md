# Digital Archaeologist operations

## VPS layout

Recommended installation path: `/opt/digital-archaeologist` with a dedicated `digital-archaeologist` OS user and virtual environment at `/opt/digital-archaeologist/.venv`.

Keep secrets and runtime configuration outside Git, for example `/etc/digital-archaeologist.env` with mode `0600`.

## Discovery schedule

The supplied systemd timer runs the read-only discovery job twice daily at approximately 03:00 and 15:00 with a randomized delay. Enable it with:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now digital-archaeologist-discovery.timer
systemctl list-timers digital-archaeologist-discovery.timer
```

## Dashboard

The dashboard service binds Streamlit to `127.0.0.1:8501`. Put an authenticated reverse proxy in front of it if remote access is required. Do not expose the Streamlit port directly to the public internet.

## Environment

Required/optional settings include:

- `DA_DATABASE_URL` — SQLite database location.
- `DA_DRY_RUN=true` and `DA_ALLOW_SIDE_EFFECTS=false` — v0.1 safety defaults.
- `DA_GITHUB_TOKEN` — optional token for higher GitHub API limits.
- `DA_GITHUB_QUERIES` — comma-separated discovery queries.
- `DA_WEB_SEEDS` — comma-separated public URLs to inspect.
- `DA_AI_PROVIDER=openai`, `DA_AI_MODEL`, and `DA_AI_API_KEY` — optional provider configuration. With no provider, investigation is not run.
- The investigation job selects the 20 highest-scoring candidates by default. It reports a human-review recommendation and never approves or pursues an opportunity automatically.

## Safety boundary

Jobs have no capability for purchasing, owner contact, domain acquisition, private-account access, deployment, or automatic publishing/forking. Investigation failures are isolated per candidate and discovery source failures are isolated per collector.

## Live validation checklist

Run from the VPS after installing dependencies and setting public-source configuration:

```bash
PYTHONPATH=src python -m digital_archaeologist.jobs.run_discovery
```

Record the number of unique candidates in SQLite. The validation target is 100 candidates, followed by manual review of the top 20 and adversarial review of promising candidates. Do not treat network errors as opportunities; failed sources remain failed evidence records and the run continues.
