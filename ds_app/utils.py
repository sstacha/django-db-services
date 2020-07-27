# import logging
import sys
from django.conf import settings
from importlib import reload
from django.urls import clear_url_caches
from django.db import connections

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


# THIS WAS THE ORACLE WAY; using the mysqlclient way
# def dictfetchstoredresults(cursor):
#     """Return all rows from a cursor as a dict from a stored procedure callable statement"""
#     if cursor.description:
#         columns = [col[0] for col in cursor.description]
#         return [
#             dict(zip(columns, row))
#             for row in cursor.stored_results().fetchall()
#         ]
#     return []
def dictfetchstoredresults(cursor):
    """
    dictfetchstoredresults will return all resultsets as rows of dictionary objects for inclusion in the
    json output
    format: [{rs0:[{row1},{row2}...]}, {rs1:...}]
    """
    resultsets = []
    rows = dictfetchall(cursor)
    i = 0
    if rows:
        resultsets.append({'rs' + str(i): rows})
    while cursor.nextset():
        rows = dictfetchall(cursor)
        if rows:
            i += 1
            resultsets.append({'rs' + str(i): rows})

    return resultsets


def dictfetchstoredparameters(cursor, callable_name, callable_args):
    """
    dictfetchstoredparams will return all param values as a dictionary for inclusion in the
    json output
    format: {param0: value0, param1: value1...}
    """
    # build our select statement for each param
    #   syntax: @_<callable_name>_<index>
    result_args_dict = {}
    if callable_args and callable_name:
        sql = "SELECT "
        for idx, arg in enumerate(callable_args):
            if len(sql) > len("SELECT "):
                sql += ", "
            sql += f"@_{callable_name}_{idx} as param{idx}"
        cursor.execute(sql)
        result_args_list = dictfetchall(cursor)
        if result_args_list:
            result_args_dict = result_args_list[0]
    return result_args_dict


def dictfetchall(cursor):
    """Return all rows from a cursor as a dict"""
    # NOTE: this has been modified to convert if results contains mysql "byte" type!
    rows = []
    meta = cursor.description
    if meta:
        columns = [col[0] for col in meta]
        types = [col[1] for col in meta]
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


def get_key_by_idx(dictionary, idx=0):
    if idx < 0:
        idx += len(dictionary)
    for i, key in enumerate(dictionary.keys()):
        if i == idx:
            return key
    raise IndexError("dictionary index out of range")


def testcp():
    # NOTE: different drivers do callable statements differently; basing this code on mysqlclient since
    #   I can't get the mysql-connector-python to tie into django 3.0.8 properly.
    #   <sigh> I have always had trouble with Oracles driver; a shame really since I like the syntax better
    #   maybe try again later
    # SEE: https://stackoverflow.com/questions/15320265/cannot-return-results-from-stored-procedure-using-python-cursor
    #   about mid way down the page for usage differences.
    with connections['eva'].cursor() as cursor:
        args = ["1", "2", "0"]
        # result_args = cursor.callproc('test_sas_proc2', args)
        # resultsets = dictfetchstoredresults(cursor)
        # mysqlclient has to issue a select which is stupid since we don't know the number of params at runtime
        cursor.callproc("test_sas_proc2", args)
        cursor.execute("""SELECT @_test_sas_proc2_0 as param1, @_test_sas_proc2_1 as param2, @_test_sas_proc2_2 as param3""")
        result_args = dictfetchall(cursor)
        print(result_args)
        # mysqlclient uses next() to iterate over multiple results
        cursor.callproc("test_sas_proc2", args)
        resultsets = [{'rs0': dictfetchall(cursor)}]
        i = 0
        while cursor.nextset():
            i += 1
            resultsets.append({'rs' + str(i): dictfetchall(cursor)})
        print(resultsets)

def test_driver():
    with connections['eva'].cursor() as cursor:
        # sql = """
        # select * from events where name = 'booger'
        # """
        sql = """
        SELECT * FROM v_Events_DL
WHERE name NOT LIKE concat('%', x'22', '%')
        """
        cursor.execute(sql)
        results = dictfetchall(cursor)
        print(results)

if __name__ == '__main__':
    print('main')
