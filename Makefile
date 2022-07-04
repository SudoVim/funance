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

.PHONY: format
format:
	@git ls-files | grep "\.py$ " | grep -v "/migrations/" | xargs $(DOCKER_COMPOSE) run web black

.PHONY: format-check
format-check:
	@git ls-files | grep "\.py$ " | grep -v "/migrations/" | xargs $(DOCKER_COMPOSE) run web black --check
