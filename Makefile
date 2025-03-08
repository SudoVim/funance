DOCKER_COMPOSE = docker compose

DOCKER_COMPOSE_RUN = $(DOCKER_COMPOSE) run --rm
DOCKER_COMPOSE_RUN_NO_DEPS = $(DOCKER_COMPOSE_RUN) --no-deps

.PHONY: run
run:
	$(DOCKER_COMPOSE) up --remove-orphans

.PHONY: start
start:
	$(DOCKER_COMPOSE) start

.PHONY: run-debug
run-debug:
	$(DOCKER_COMPOSE) run -ti -p 8000:8000 web python manage.py runserver 0.0.0.0:8000

.PHONY: stop
stop:
	$(DOCKER_COMPOSE) stop

.PHONY: status
status:
	$(DOCKER_COMPOSE) ps

.PHONY: build
build:
	$(DOCKER_COMPOSE) build

.PHONY: bash
bash:
	$(DOCKER_COMPOSE_RUN) web bash

.PHONY: shell
shell:
	$(DOCKER_COMPOSE_RUN) web python manage.py shell

.PHONY: test
test:
	$(DOCKER_COMPOSE_RUN) web python manage.py test

.PHONY: test-fast
test-fast:
	$(DOCKER_COMPOSE_RUN) web python manage.py test --parallel

.PHONY: pyright
pyright:
	$(DOCKER_COMPOSE_RUN_NO_DEPS) web basedpyright --warnings

.PHONY: ruff-check
ruff-check:
	$(DOCKER_COMPOSE_RUN_NO_DEPS) web ruff check

.PHONY: lint
lint: ruff-check pyright

.PHONY: format
format:
	$(DOCKER_COMPOSE_RUN_NO_DEPS) web sh -c "ruff check --select I --fix && ruff format"

.PHONY: fastci
fastci: format lint test-fast

.PHONY: sci
sci: format lint test

.PHONY: ci
ci: sci build-docs

.PHONY: migrate
migrate:
	$(DOCKER_COMPOSE_RUN) web python manage.py locked_migrate

.PHONY: migrations
migrations:
	$(DOCKER_COMPOSE_RUN) web python manage.py makemigrations
