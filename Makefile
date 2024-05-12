DOCKER_COMPOSE = docker-compose

.PHONY: build
build:
	$(DOCKER_COMPOSE) build

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
	@git ls-files | grep "\.py$ " | grep -v "/migrations/" | xargs pipenv run black

.PHONY: format-check
format-check:
	@git ls-files | grep "\.py$ " | grep -v "/migrations/" | xargs pipenv run black --check
