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
	$(DOCKER_COMPOSE) stop web
	$(DOCKER_COMPOSE) run -ti -p 8005:8005 web python manage.py runserver 0.0.0.0:8005

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
	$(DOCKER_COMPOSE_RUN_NO_DEPS) web ruff check --select I --fix
	$(DOCKER_COMPOSE_RUN_NO_DEPS) web ruff format

.PHONY: fastci
fastci: format lint test-fast

.PHONY: migrate
migrate:
	$(DOCKER_COMPOSE_RUN) web python manage.py migrate

.PHONY: migrations
migrations:
	$(DOCKER_COMPOSE_RUN) web python manage.py makemigrations

.PHONY: restart-scheduler
restart-scheduler:
	$(DOCKER_COMPOSE) restart scheduler

.PHONY: restart-worker
restart-worker:
	$(DOCKER_COMPOSE) restart worker

.PHONY: restart-web
restart-web:
	$(DOCKER_COMPOSE) restart web

.PHONY: restart-all
restart-all:
	$(MAKE) restart-worker
	$(MAKE) restart-scheduler
	$(MAKE) restart-web
