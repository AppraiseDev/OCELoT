
setup:
	pip install -r requirements-dev.txt
	python manage.py migrate

test:
	python manage.py check
	OCELOT_SECRET_KEY="not-so-secret-key" python manage.py test

run:
	OCELOT_SECRET_KEY="not-so-secret-key" python manage.py runserver
