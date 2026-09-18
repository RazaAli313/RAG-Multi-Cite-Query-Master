SHELL=/bin/bash


cr_compose     := docker compose -f docker-compose.cr.yml
dev_compose    := docker compose -f docker-compose.dev.yml
stage_compose  := docker compose -f docker-compose.stage.yml
prod_compose   := docker compose -f docker-compose.prod.yml
test_compose   := docker compose -f docker-compose.test.yml --env-file config/env/.test
success        := success
secrets        := . /secrets/app.env &&

%.all: %.build %.up.d
	@echo $(success)

%.deploy: %.build %.down %.secrets.wait %.up.d %.secret.reload %.migrate %.collectstatic
	@echo $(success)

%.build:
	@$($*_compose) build

%.up:
	@$($*_compose) up

%.up.d:
	@$($*_compose) up -d

%.down:
	@$($*_compose) down --remove-orphans

%.restart:
	@$($*_compose) restart

%.secret.reload:
	@set -e; \
	available_services="$($*_compose config --services)"; \
	available_services="${available_services//$'\n'/ }"; \
	for service in django celery celery_beat flower; do \
		if [[ " $$available_services " == *" $$service "* ]]; then \
			$($*_compose) restart "$$service"; \
		fi; \
	done; \

%.secrets.wait:
	@$($*_compose) up -d infisical-agent
	@echo "Waiting for Infisical secrets..."
	@until $($*_compose) exec -T infisical-agent sh -c '[ -s /secrets/app.env ]'; do sleep 2; done
	@echo "Infisical secrets ready."

%.logs:
	@$($*_compose) logs -f

cr:
	@$($@_compose) up --build
	@$($@_compose) down

%.dcshell:
	@$($*_compose) exec django bash -c '$(secrets) exec bash'

%.sp:
	@$($*_compose) exec django sh -c '$(secrets) python manage.py shell_plus'

%.attach:
	@docker attach $*

%.makemigrations:
	@$($*_compose) exec django sh -c '$(secrets) python manage.py makemigrations'

%.migrate:
	@$($*_compose) exec django sh -c '$(secrets) python manage.py migrate'

%.collectstatic:
	@$($*_compose) exec django sh -c '$(secrets) python manage.py collectstatic --noinput'

test:
	@$($@_compose) up --build -d django
	@$($@_compose) exec -T django python manage.py migrate
	@$($@_compose) exec -T django python manage.py collectstatic --no-input
	@$($@_compose) exec -T django python -m coverage run --source=. manage.py test --no-input
	@$($@_compose) exec -T django python -m coverage html -d htmlcov
	@$($@_compose) down --remove-orphans

%.psql:
	@$($*_compose) exec postgres psql -U postgres

%.rediscli:
	@$($*_compose) exec redis redis-cli -h redis
