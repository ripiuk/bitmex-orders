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

venv-init:
	if [ ! -e "venv/bin/activate" ]; then $(PYTHON) -m venv venv ; fi;
	bash -c "source venv/bin/activate && \
		pip install --upgrade wheel pip setuptools && \
		pip install --upgrade --requirement requirements.txt"


# ----- Update -----

update: venv-init

update-dev: venv-init
	bash -c "source venv/bin/activate && \
		pip install --upgrade --requirement requirements-dev.txt"


# ----- Setup -----

setup: install venv-init

setup-test: install update-dev


# ----- Run -----

run:
	bash -c "source venv/bin/activate && \
		python -m webbrowser -t 'http://127.0.0.1:8000/orders' && \
		python manage.py runserver"

run-ws-client:
	bash -c "source venv/bin/activate && \
		python -m websockets 'ws://localhost:8000/instrument/'"


# ----- Tests -----

test: update-dev
	bash -c "source venv/bin/activate && \
		python manage.py test && flake8"

test-cov: update-dev
	bash -c "source venv/bin/activate && \
		coverage run --source='.' manage.py test && \
		coverage report && coverage html && \
		python -m webbrowser -t 'htmlcov/index.html'"
