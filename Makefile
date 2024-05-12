DOCKER_COMPOSE = docker-compose

.PHONY: build
build:
	./scripts/build.sh

.PHONY: start
start:
	$(DOCKER_COMPOSE) up -d

.PHONY: run
run:
	$(DOCKER_COMPOSE) up

.PHONY: stop
stop:
	$(DOCKER_COMPOSE) stop

.PHONY: shell
shell:
	@$(DOCKER_COMPOSE) run web bash

.PHONY: django-shell
django-shell:
	@$(DOCKER_COMPOSE) run web pipenv run python ./manage.py shell

.PHONY: test
test:
	@$(DOCKER_COMPOSE) run web pipenv run python ./manage.py test

.PHONY: format
format:
	@$(DOCKER_COMPOSE) run web pipenv run black --exclude '(/migrations/|.venv/)' .

.PHONY: format-check
format-check:
	@$(DOCKER_COMPOSE) run web pipenv run black --exclude '(/migrations/|.venv/)' . --check

.PHONY: mypy
mypy:
	@$(DOCKER_COMPOSE) run web pipenv run mypy .
