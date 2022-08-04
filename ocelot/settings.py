"""
Django settings for ocelot project.

Generated by 'django-admin startproject' using Django 2.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""
import logging
import os
from logging.handlers import (  # pylint: disable=ungrouped-imports
    RotatingFileHandler,
)


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

DEBUG = os.environ.get('OCELOT_DEBUG', True)

ADMINS = os.environ.get('OCELOT_ADMINS', ())
MANAGERS = ADMINS

SECRET_KEY = os.environ.get(
    'OCELOT_SECRET_KEY'
)  # Throw if no SECRET_KEY set!
ALLOWED_HOSTS = os.environ.get('OCELOT_ALLOWED_HOSTS', '127.0.0.1').split(
    ','
)

CSRF_TRUSTED_ORIGINS = ['https://{0}'.format(x) for x in ALLOWED_HOSTS]

WSGI_APPLICATION = os.environ.get(
    'OCELOT_WSGI_APPLICATION', 'ocelot.wsgi.application'
)

# Try to load database settings, otherwise use defaults.
DB_ENGINE = os.environ.get('OCELOT_DB_ENGINE')
DB_NAME = os.environ.get('OCELOT_DB_NAME')
DB_USER = os.environ.get('OCELOT_DB_USER')
DB_PASSWORD = os.environ.get('OCELOT_DB_PASSWORD')
DB_HOST = os.environ.get('OCELOT_DB_HOST')
DB_PORT = os.environ.get('OCELOT_DB_PORT')

if all((DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)):
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
            'OPTIONS': {'sslmode': 'require'},
        }
    }

else:

    # Database
    # https://docs.djangoproject.com/en/2.2/ref/settings/#databases

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

FILE_UPLOAD_PERMISSIONS = 0o644

# Logging settings for this Django project.
LOG_LEVEL = logging.DEBUG
LOG_FILENAME = os.path.join(BASE_DIR, 'ocelot.log')
LOG_FORMAT = "[%(asctime)s] %(name)s::%(levelname)s %(message)s"
LOG_DATE = "%m/%d/%Y @ %H:%M:%S"
LOG_FORMATTER = logging.Formatter(LOG_FORMAT, LOG_DATE)
LOG_HANDLER = RotatingFileHandler(
    filename=LOG_FILENAME,
    mode="a",
    maxBytes=50 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
LOG_HANDLER.setLevel(level=LOG_LEVEL)
LOG_HANDLER.setFormatter(LOG_FORMATTER)


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'leaderboard',
    'evaluation',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ocelot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'ocelot.context_processors.project_version',
            ]
        },
    }
]


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Static files that are not tied to a particular app should be put there
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'assets'),
]

# Allow to specify absolute filesystem path to the directory that will hold user-uploaded files.
MEDIA_ROOT = os.environ.get('OCELOT_MEDIA_ROOT', '')

# Project version
# See point 4 from https://packaging.python.org/guides/single-sourcing-package-version/

with open(os.path.join(BASE_DIR, 'VERSION')) as version_file:
    VERSION = version_file.read().strip()
