PYTHON = python3.8

PSQL_USER = oleksandr
PSQL_PASSWORD = oleksandr
PSQL_DB = bitmex_orders

# ========== Linux (Debian) ==========


# ----- Install -----

install:
	$(if $(shell apt-cache search $(PYTHON)), , \
		sudo add-apt-repository -y ppa:fkrull/deadsnakes && apt-get update)
	sudo apt-get install -y build-essential
	sudo apt-get install -y $(PYTHON) $(PYTHON)-dev $(PYTHON)-venv cython

install-psql:
	sudo apt-get -q update \
	&& apt-get install -y postgresql postgresql-contrib postgresql-server-dev-10
	sudo -u postgres psql -c "CREATE USER $(PSQL_USER) with password '$(PSQL_PASSWORD)'"
	sudo -u postgres psql -c "ALTER ROLE $(PSQL_USER) SET client_encoding TO 'utf8'"
	sudo -u postgres psql -c "ALTER ROLE $(PSQL_USER) SET default_transaction_isolation TO 'read committed'"
	sudo -u postgres psql -c "ALTER ROLE $(PSQL_USER) SET timezone TO 'UTC'"
	sudo -u postgres psql -c "CREATE DATABASE $(PSQL_DB) OWNER $(PSQL_USER)"
	sudo -u postgres psql -c "ALTER USER $(PSQL_USER) CREATEDB"


# ----- Virtualenv -----

venv:
	@if [ ! -d "venv" ]; then $(PYTHON) -m venv venv ; fi;


# ----- Update -----

update:
	@echo "----- Updating requirements -----"
	@export XXHASH_FORCE_CFFI=1
	@pip install --upgrade wheel pip
	@pip install --upgrade --requirement requirements.txt


# ----- Setup -----

setup: install venv
	@bash -c "source venv/bin/activate && $(MAKE) update"


# ----- Run -----

run:
	xdg-open "http://127.0.0.1:8000/"
	python manage.py runserver
