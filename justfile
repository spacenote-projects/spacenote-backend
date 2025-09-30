set dotenv-load
set shell := ["bash", "-cu"] # Always use bash so &&, ||, and redirects work predictably

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist src/*.egg-info

sync:
    uv sync --all-extras

build: clean lint audit test
    uv build

format:
    uv run ruff check --select I --fix src
    uv run ruff format src

lint *args: format
    uv run ruff check {{args}} src tests
    uv run mypy src

outdated:
    uv pip list --outdated

audit:
    uv export --no-dev --all-extras --format requirements-txt --no-emit-project > requirements.txt
    uv run pip-audit -r requirements.txt --disable-pip
    rm requirements.txt
    uv run bandit --silent --recursive --configfile "pyproject.toml" src

test:
    uv run pytest tests

dev: # For human devs
    uv run python -m watchfiles "python -m spacenote.main" src

agent-start: agent-stop # For AI agents
    sh -c 'SPACENOTE_PORT=3101 uv run python -m spacenote.main > agent.log 2>&1 & echo $! > agent.pid'

agent-stop: # For AI agents
    -pkill -F agent.pid 2>/dev/null || true
    -rm -f agent.pid agent.log

# Docker commands
docker-build:
    docker buildx build --platform linux/amd64,linux/arm64 \
        --build-arg GIT_COMMIT_HASH=$(git rev-parse --short HEAD) \
        --build-arg GIT_COMMIT_DATE=$(git log -1 --format=%cI) \
        --build-arg BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
        -t spacenote-backend:latest .

docker-push tag="latest":
    docker buildx build --platform linux/amd64,linux/arm64 \
        --build-arg GIT_COMMIT_HASH=$(git rev-parse --short HEAD) \
        --build-arg GIT_COMMIT_DATE=$(git log -1 --format=%cI) \
        --build-arg BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
        -t ghcr.io/spacenote-projects/spacenote-backend:{{tag}} --push .

docker-run-local:
    docker run --rm \
        --name spacenote-test \
        -p 8000:8000 \
        -e SPACENOTE_DATABASE_URL="${SPACENOTE_DATABASE_URL//127.0.0.1/host.docker.internal}" \
        -e SPACENOTE_SESSION_SECRET_KEY="${SPACENOTE_SESSION_SECRET_KEY}" \
        -e SPACENOTE_CORS_ORIGINS="${SPACENOTE_CORS_ORIGINS}" \
        -e SPACENOTE_FRONTEND_URL="${SPACENOTE_FRONTEND_URL}" \
        spacenote-backend:latest
