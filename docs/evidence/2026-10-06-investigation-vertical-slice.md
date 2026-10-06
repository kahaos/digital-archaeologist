# Investigation vertical slice — run evidence

Run date: 2026-10-06 (UTC)

Discovery run ID: `6dc96929147a44dea0f0c2dbcf4cbc1c`

## Implementation and tests

Files changed for this implementation:

- `.env.example`, `docs/operations.md`
- `src/digital_archaeologist/config.py`
- `src/digital_archaeologist/domain/models.py`
- `src/digital_archaeologist/dashboard/app.py`, `src/digital_archaeologist/dashboard/views.py`
- `src/digital_archaeologist/jobs/run_investigation.py`
- `src/digital_archaeologist/research/__init__.py`
- `src/digital_archaeologist/research/evidence.py` (new)
- `src/digital_archaeologist/research/investigator.py`
- `src/digital_archaeologist/research/prompts.py`
- `src/digital_archaeologist/research/provider.py`
- `src/digital_archaeologist/research/validator.py`
- `src/digital_archaeologist/storage/database.py`, `src/digital_archaeologist/storage/repositories.py`
- This evidence file.

Tests added or modified:

- Added GitHub/web evidence collection, provider adapter, and provider-configuration tests in `tests/research/test_evidence.py` and `tests/research/test_provider.py`.
- Modified `tests/research/test_investigator.py` and `tests/research/test_validator.py` for source-ID citations, evidence-type rules, adversarial findings, report persistence, and the human-review boundary.
- Modified `tests/jobs/test_jobs.py` for top-20 ordering, scores below the former threshold, status handling, and absent-provider behavior.
- Modified `tests/storage/test_repositories.py` for additive migration of existing report/evidence tables.
- Modified `tests/dashboard/test_views.py`, `tests/e2e/test_mvp_pipeline.py`, and `tests/test_config.py` for persisted review output, source-backed findings, human-review wording, and provider model configuration.

Full test run: `pytest -q` — **51 passed in 0.50s**.

## Discovery and selection

The discovery command returned `discovered=204, new=0, duplicates=0, failed=0, scoreable=204`. The database contained 204 scored candidates and no existing opportunity reports. The investigation job's default selection is the 20 highest scores, sorted by score descending and canonical identity for ties. The selected candidates and stored deterministic scores were:

| Rank | Deterministic score | Repository/project | URL |
|---:|---:|---|---|
| 1 | 61.0624 | ExoPlayer | https://github.com/google/ExoPlayer |
| 2 | 61.0139 | gaia | https://github.com/mozilla-b2g/gaia |
| 3 | 60.8090 | darkstar | https://github.com/DarkstarProject/darkstar |
| 4 | 58.4629 | quilt | https://github.com/Shopify/quilt |
| 5 | 57.8375 | yobi | https://github.com/naver/yobi |
| 6 | 55.9343 | specification | https://github.com/opentracing/specification |
| 7 | 54.6174 | pyflame | https://github.com/uber-archive/pyflame |
| 8 | 53.3433 | playdoh | https://github.com/mozilla/playdoh |
| 9 | 53.2076 | chatgpt-google-extension | https://github.com/wong2/chatgpt-google-extension |
| 10 | 52.9485 | tmpnb | https://github.com/jupyter/tmpnb |
| 11 | 52.6637 | onedrive-cf-index | https://github.com/spencerwooo/onedrive-cf-index |
| 12 | 51.9123 | android-crop | https://github.com/jdamcd/android-crop |
| 13 | 51.7464 | django-knowledge | https://github.com/zapier/django-knowledge |
| 14 | 51.6487 | cmsplugin-filer | https://github.com/django-cms/cmsplugin-filer |
| 15 | 50.3262 | teaching-app-dev-swift | https://github.com/SwiftEducation/teaching-app-dev-swift |
| 16 | 50.0418 | tango-examples-c | https://github.com/googlearchive/tango-examples-c |
| 17 | 49.7336 | cherami-server | https://github.com/uber-archive/cherami-server |
| 18 | 49.5321 | wpsnapshots | https://github.com/10up/wpsnapshots |
| 19 | 49.4875 | tango-examples-unity | https://github.com/googlearchive/tango-examples-unity |
| 20 | 49.2524 | cpustat | https://github.com/uber-archive/cpustat |

## Provider and investigation result

Provider configuration observed in this environment:

- `DA_AI_PROVIDER=none`
- `DA_AI_MODEL` defaults to `gpt-4o-mini` but was not used.
- `DA_AI_API_KEY` was unavailable; no credential value is recorded here.
- `OPENAI_API_KEY` was unavailable; no credential value is recorded here.

**Real provider investigation NOT RUN — provider credentials/configuration unavailable.** Zero candidates were investigated. No investigation-stage evidence sources were fetched, no investigation Evidence IDs were created, and no investigation provenance or reports were produced. Therefore there are no provider findings, adversarial findings, or candidates rejected by investigation in this run. The top-20 URLs above are discovery provenance, not investigation evidence.

## Evidence-label examples from this run

- **OBSERVED (discovery result only):** the live GitHub discovery result for ExoPlayer reported 21,943 stars, 5,992 forks, 627 open issues, `archived=false`, licence `Apache-2.0`, and `updated_at=2026-10-05T23:52:26Z`. The candidate provenance URL is https://github.com/google/ExoPlayer. This is collected discovery metadata, not an investigation Evidence record.
- **INFERRED:** no runtime example; no model investigation ran.
- **ESTIMATED:** no runtime example; no model investigation ran.
- **UNKNOWN:** no model-generated UNKNOWN finding exists. Investigation-time competition, buyer demand, operating costs, and revenue remain unresearched in this run; that absence is not a finding about any individual candidate.

The implementation reserves OBSERVED for collector-created source records. Model-produced INFERRED/ESTIMATED claims must cite IDs from the collected source set; estimates require assumptions. UNKNOWN claims must explain what remains unknown. Those rules were exercised by tests, not by real provider output in this run.

## Limitations and remaining work

- A real run still requires configuring `DA_AI_PROVIDER=openai` and `DA_AI_API_KEY`, then running the top-20 job. No real research or adversarial conclusions are available yet.
- Current collection uses GitHub repository metadata and recent non-PR issue records, or the existing public-page inspector for web candidates. It does not establish willingness to pay, market size, competitor coverage, or acquisition economics.
- Retrieval failure marks that candidate investigation failed and leaves it retryable; failed-source details are logged rather than saved as UNKNOWN evidence.
- The provider response is JSON-parsed and strictly validated locally. The provider adapter and request/response path were tested with a mocked HTTP transport only; live API behavior was not verified.
- A successful report changes candidate state to WATCH/IGNORE/REJECTED and always requires human review before any action. No candidate is automatically marked PURSUE, acquired, or approved.
