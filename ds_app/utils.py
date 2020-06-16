# import logging
import sys
from django.conf import settings
from importlib import reload
from django.urls import clear_url_caches


class TermColor:
    def __init__(self):
        pass

    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# NOTE: reloading the main settings.ROOT_URLCONF will not reload other imported modules!
def reload_urls(urls_module_name=None):
    if not urls_module_name:
        urls_module_name = settings.ROOT_URLCONF
    if urls_module_name in sys.modules:
        clear_url_caches()
        reload(sys.modules[urls_module_name])
# see also: http://codeinthehole.com/writing/how-to-reload-djangos-url-config/


def reload_app_urls():
    """
    Clears the app cache and the main cache for ds_app; seems to be working with both!
    :return: None
    """
    root_urls = settings.ROOT_URLCONF
    app_urls = 'ds_app.urls'
    if app_urls in sys.modules:
        clear_url_caches()
        reload(sys.modules[app_urls])
    if root_urls in sys.modules:
        clear_url_caches()
        reload(sys.modules[root_urls])


def dictfetchstoredresults(cursor):
    """Return all rows from a cursor as a dict from a stored procedure callable statement"""
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.stored_results().fetchall()
    ]


def dictfetchall(cursor):
    """Return all rows from a cursor as a dict"""
    # NOTE: this has been modified to convert if results contains mysql "byte" type!
    meta = cursor.description
    columns = [col[0] for col in meta]
    types = [col[1] for col in meta]
    rows = []
    convert = 16 in types
    for row in cursor.fetchall():
        new_row = []
        # ensure each row that is a byte type is converted to integer?
        if convert:
            i = 0
            for field_value in row:
                if types[i] == 16:
                    new_row.append(int.from_bytes(field_value, "big"))
                else:
                    new_row.append(field_value)
                i = i + 1
        if new_row:
            rows.append(dict(zip(columns, new_row)))
        else:
            rows.append(dict(zip(columns, row)))
    return rows


def dictfetchall_original(cursor):
    """Return all rows from a cursor as a dict"""
    # NOTE: this is the original code that does not work with mysql "byte" type!
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


if __name__ == '__main__':
    print('main')
