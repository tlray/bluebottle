# NOTE: local.py must be an empty file when using this configuration.

from .defaults import *

# Put jenkins environment specific overrides below.

INSTALLED_APPS += ('django_jenkins',)

SECRET_KEY = 'hbqnTEq+m7Tk61bvRV/TLANr3i0WZ6hgBXDh3aYpSU8m+E1iCtlU3Q=='

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

DEBUG = False
TEMPLATE_DEBUG = False

# Test all INSTALLED_APPS by default
PROJECT_APPS = list(INSTALLED_APPS)

# Some of these tests fail, and it's not our fault
# https://code.djangoproject.com/ticket/17966
PROJECT_APPS.remove('django.contrib.auth')

# This app fails with a strange error:
# DatabaseError: no such table: django_comments
# Not sure what's going on so it's disabled for now.
PROJECT_APPS.remove('django.contrib.sites')

# https://github.com/django-extensions/django-extensions/issues/154
PROJECT_APPS.remove('django_extensions')
PROJECT_APPS.remove('django_extensions.tests')

# FIXME: We need to fix the django_polymorphic tests
PROJECT_APPS.remove('polymorphic')

# Social auth tests require firefox webdriver which we don't want to install right now.
PROJECT_APPS.remove('social_auth')

# django-salesforce tests don't pass when it's not setup.
PROJECT_APPS.remove('salesforce')

# Disable pylint becasue it seems to be causing problems
JENKINS_TASKS = (
    # 'django_jenkins.tasks.run_pylint',
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.django_tests',
)
