# Status — Fleet Work Trial

## Done
- `scrape_prs.py` — written with all filters (linked issue, noise title, doc-only, max files, source+test required)
- `candidates_psf_requests.json` — 40 candidates scraped for `psf/requests`
- Dockerfile templates for all 4 repos (requests, click, flask, httpx) in `templates/`
- `build_task.py` — materializes candidates → `tasks/task_XXX/{task.json, Dockerfile, eval_script.sh}`
- `validate_task.py` — two-canary Docker validation
- `push_images.py` — parallel build + push to registry
- `harbor-train/` — SkyRL repo cloned locally

## In Progress
- Scraping other 3 repos — click, flask, httpx not scraped yet

## Known Bugs to Fix Before Build
1. Dockerfile has `/workspace` but validate_task.py expects `/repo` — need to align to `/repo`
2. `build_task.py` does string replace of `${BASE_COMMIT}` — works, but `ARG BASE_COMMIT` line in template is dead weight (harmless)
3. `DOCKER_REGISTRY` in `.env` is empty — need to set before push

## Next Steps (in order)
1. **Scrape** — `uv run scripts/scrape_prs.py pallets/click pallets/flask encode/httpx`
2. **Fix Dockerfile** — change `/workspace` → `/repo` in all 4 templates
3. **Build tasks** — `uv run scripts/build_task.py tasks/candidates_psf_requests.json` (test with requests first)
4. **Validate** — `uv run scripts/validate_task.py` (runs Docker canary tests, ~30-60 min)
5. **Set DOCKER_REGISTRY** in `.env`, then push — `uv run scripts/push_images.py`
6. **Part 2** — SkyRL/Harbor training on GCP with generated tasks
7. **Part 3** — OOD eval on SWE-bench Verified subset

## Blockers
- Need to scrape click/flask/httpx before building tasks for those repos
- Docker must be running locally for validate + build steps


======
# Work Trial Status

## Done
- Scraped PRs from `psf/requests` → 40 task candidates
- Scraping `pallets/click`, `pallets/flask`, `encode/httpx` (running now)
- Written scripts: scrape, build, validate, push
- Dockerfile templates for all 4 repos (bug fixed: /workspace → /repo)
- Cloned SkyRL/Harbor training repo (`harbor-train/`)
- Read through the training pipeline code

## In Progress
- Scraper running for click/flask/httpx

## Not Started
- Building task folders (`tasks/task_XXX/`) from candidates
- Validating tasks (Docker canary tests)
- Pushing images to GCR
- Training run on GCP

## Key Open Question (for colleague)
The training code uses **OpenHands runtime** to run the agent inside containers —
not a simple `docker run`. We need to know:

> Does training require a running OpenHands runtime server, or is there a simpler
> path that runs our `eval_script.sh` directly against our Docker images?

The answer determines how we wire our task images into the training loop.

## What's Working End-to-End
Nothing yet — we haven't built or validated a single task instance.
The next milestone is: build 1 task → validate it passes both canaries → push to GCR.