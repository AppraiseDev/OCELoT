
setup:
	pip install -r requirements-dev.txt
	python manage.py migrate

test:
	python manage.py test

run:
	python manage.py runserver
