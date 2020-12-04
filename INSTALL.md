# OCELoT

## Basic setup

1. Install Python 3.5+.
2. Clone the repository:

        git clone https://github.com/AppraiseDev/OCELoT
        cd OCELoT

3. Install virtual environments for Python:

        pip3 install --user virtualenv

4. Create environment for the project, activate it, and install Python
   requirements:

        virtualenv venv -p python3
        source venv/bin/activate
        pip install -r requirements.txt

5. Create database, the first super user, and collect static files:

        python manage.py migrate
        python manage.py createsuperuser
        python manage.py collectstatic

    Follow instructions on your screen; do not leave the password empty.

6. Run the app on a local server:

        python manage.py runserver

    Open the browser at http://127.0.0.1:8000/.
    The admin panel is available at http://127.0.0.1:8000/admin

