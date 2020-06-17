"""
Django settings for ds project.

Generated by 'django-admin startproject' using Django 3.0.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
# default BASE_DIR = PROJECT_DIR
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# APP_DIR is the main application directory (ds for us)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_DIR is the directory that is the django project (also ds for us)
# NOTE: for this app the BASE_DIR is the same as PROJECT_DIR
PROJECT_DIR = os.path.dirname(APP_DIR)
# we will go ahead and check in our static files for this app so it doesn't have to be done on the server
STATIC_DIR = os.path.join(BASE_DIR, 'static')
# DATA_DIR: is the directory containing our data (ds/content for this app)
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '+^=p!b51_v^7h!^@11_wwmvhxpj*s^ti)n5(=jouwt230u4j!z'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_ROOT = STATIC_DIR

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ds_app.apps.DsAppConfig',
    'import_export',
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

ROOT_URLCONF = 'ds.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ds.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
# localhost can be 127.0.0.1 on our laptops but needs to be host.docker.internal to resolve to the host under docker
# NOTE: environment should only get set if docker compose or we set on our laptop env to localhost
localhost = os.environ.get('LOCALHOST', 'localhost')
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DATA_DIR, 'db.sqlite3'),
    },
}
# try to append any database endpoint connections defined for this environment
#   NOTE: it is assumed we will place this file on the server for each environment for reading
#       and mount it into the container
with open('data/endpoint_databases_dict.txt', 'r') as f:
    s = f.read()
    # print(f's: {s}')
    ENDPOINT_DATABASES = eval(s)
    if ENDPOINT_DATABASES:
        DATABASES.update(ENDPOINT_DATABASES)

# print(f'endpoint databases: {ENDPOINT_DATABASES}')
# print('')
# print(f'DATABASES: {DATABASES}')
# print('')

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'root': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'ds': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'werkzeug': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'docroot': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'ds_app': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

# Replace any UWEB_ prefixed environment variables in settings at startup
#   NOTE: used for docker/local machine environment variable loading overrides
# 	NOTE: expect strings not complex items like below
this_module = sys.modules[__name__]
for k, v in os.environ.items():
    if k.startswith("UWEB_"):
        attr_key = k[5:]
        if attr_key:
            print(f"env: setting {attr_key} to [{str(v)}]")
            setattr(this_module, attr_key, v)



    # 'publications': {
    #     'ENGINE': 'django.db.backends.mysql',
    #     'HOST': localhost,
    #     # 'HOST': 'localhost',
    #     'NAME': 'django',
    #     'PORT': '3306',
    #     'USER': 'root',
    #     'PASSWORD': 'root',
    # },
    # 'web_cache': {
    #     'ENGINE': 'django.db.backends.mysql',
    #     'HOST': localhost,
    #     # 'HOST': 'localhost',
    #     'NAME': 'web_cache',
    #     'PORT': '3306',
    #     'USER': 'root',
    #     'PASSWORD': 'root',
    # },
    # 'events': {
    #     'ENGINE': 'django.db.backends.mysql',
    #     'HOST': localhost,
    #     # 'HOST': 'localhost',
    #     'NAME': 'djangoevents',
    #     'PORT': '3306',
    #     'USER': 'root',
    #     'PASSWORD': 'root',
    # },
    # 'web': {
    #     'ENGINE': 'django.db.backends.mysql',
    #     'HOST': localhost,
    #     # 'HOST': 'localhost',
    #     'NAME': 'djangoweb',
    #     'PORT': '3306',
    #     'USER': 'root',
    #     'PASSWORD': 'root',
    # },
    # 'enterprise_data': {
    #     'ENGINE': 'django.db.backends.mysql',
    #     'HOST': localhost,
    #     # 'HOST': 'localhost',
    #     'NAME': 'enterprise_data',
    #     'PORT': '3306',
    #     'USER': 'root',
    #     'PASSWORD': 'root',
    # },
    # 'eva': {
    #     'ENGINE': 'django.db.backends.mysql',
    #     'HOST': localhost,
    #     # 'HOST': 'localhost',
    #     'NAME': 'eva',
    #     'PORT': '3306',
    #     'USER': 'root',
    #     'PASSWORD': 'root',
    # }
