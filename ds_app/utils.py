# import logging
import sys
import io
import datetime
from io import StringIO
from django.conf import settings
from importlib import reload
from django.urls import clear_url_caches
from django.db import connections, IntegrityError, DatabaseError
from contextlib import redirect_stdout
import logging
from collections import namedtuple


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
    F_Default = "\x1b[39m"
    F_Black = "\x1b[30m"
    F_Red = "\x1b[31m"
    F_Green = "\x1b[32m"
    F_Yellow = "\x1b[33m"
    F_Blue = "\x1b[34m"
    F_Magenta = "\x1b[35m"
    F_Cyan = "\x1b[36m"
    F_LightGray = "\x1b[37m"
    F_DarkGray = "\x1b[90m"
    F_LightRed = "\x1b[91m"
    F_LightGreen = "\x1b[92m"
    F_LightYellow = "\x1b[93m"
    F_LightBlue = "\x1b[94m"
    F_LightMagenta = "\x1b[95m"
    F_LightCyan = "\x1b[96m"


class LogBuffer:
    """
    Captures all logging to a buffer; simulates the logging library methods and levels
    """
    # constants for picking the log_level and determining if we log to console based on it
    LOG_DEBUG = logging.DEBUG
    LOG_INFO = logging.INFO
    LOG_WARN = logging.WARNING
    LOG_FATAL = logging.FATAL
    LOG_ALWAYS = 99
    LOG_SPACE = 999

    _buffer = ""

    def __init__(self, name: str = None, logger: logging.Logger = None, level: int = None, color_output: bool = False,
                 echo: bool = False) -> None:
        self.name = name
        self.logger = logger or logging.getLogger(name)
        if level is None:
            self._level = self.logger.getEffectiveLevel()
        else:
            self._level = level
        self.level = self._level
        self.color_output = color_output
        self.echo = echo

    # logging helper functions
    def debug(self, msg):
        self.log(msg, self.LOG_DEBUG)

    def info(self, msg, color_output=None):
        self.log(msg, self.LOG_INFO, color_output)

    def warning(self, msg, color_output=None):
        self.log(msg, self.LOG_WARN, color_output)

    def fatal(self, msg, color_output=None):
        self.log(msg, self.LOG_FATAL, color_output)

    def always(self, msg, color_output=None):
        self.log(msg, self.LOG_ALWAYS, color_output)

    def log(self, msg, log_level, color_output=None):
        if log_level >= self.level:
            c_msg = str(msg)
            color = color_output or self.color_output
            if color:
                if log_level == self.LOG_DEBUG:
                    c_msg = self.format_msg(log_level, msg)
                if log_level == self.LOG_INFO:
                    c_msg = TermColor.OKBLUE + self.format_msg(log_level, msg) + TermColor.ENDC
                if log_level == self.LOG_WARN:
                    c_msg = TermColor.WARNING + self.format_msg(log_level, msg) + TermColor.ENDC
                if log_level == self.LOG_FATAL:
                    c_msg = TermColor.FAIL + self.format_msg(log_level, msg) + TermColor.ENDC
                if log_level == self.LOG_ALWAYS:
                    c_msg = TermColor.F_DarkGray + self.format_msg(log_level, msg) + TermColor.ENDC
            self._buffer += c_msg + "\n"
            if self.echo:
                self.logger.log(log_level, c_msg)

    def clear(self) -> None:
        self._buffer = ""
        self.level = self._level

    def __str__(self):
        return self._buffer

    def format_msg(self, log_level: int, c_msg: str) -> str:
        # later may add formatting separately like logging but static for now
        if log_level == self.LOG_SPACE:
            msg = f"{self.get_status(log_level)} {''.ljust(19)} {c_msg}"
        else:
            msg = f"{self.get_status(log_level)} {self.get_time()} {c_msg}"
        return msg

    def get_status(self, log_level: int) -> str:
        if log_level == self.LOG_DEBUG:
            return "DEBUG".ljust(5)
        if log_level == self.LOG_INFO:
            return "INFO".ljust(5)
        if log_level == self.LOG_WARN:
            return "WARN".ljust(5)
        if log_level == self.LOG_FATAL:
            return "FATAL".ljust(5)
        if log_level == self.LOG_ALWAYS:
            return "TRACE".ljust(5)
        return "".ljust(5)

    @staticmethod
    def get_time() -> str:
        return f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S%z}'


# class ColorLogger:
#     """
#     Class to encapsulate methods and data for logging at a specific log level with terminal colors
#     """
#     # constants for picking the log_level and determining if we log to console based on it
#     LOG_DEBUG = 0
#     LOG_INFO = 1
#     LOG_WARN = 2
#     LOG_FATAL = 3
#     LOG_ALWAYS = 4
#
#     def __init__(self, name, level=LOG_FATAL):
#         self.name = name
#         self.level = level
#
#     # logging helper functions
#     def debug(self, msg):
#         self.log(msg, self.LOG_DEBUG)
#
#     def info(self, msg, color_output=True):
#         self.log(msg, self.LOG_INFO, color_output)
#
#     def warn(self, msg, color_output=True):
#         self.log(msg, self.LOG_WARN, color_output)
#
#     def fatal(self, msg, color_output=True):
#         self.log(msg, self.LOG_FATAL, color_output)
#
#     def always(self, msg, color_output=True):
#         self.log(msg, self.LOG_ALWAYS, color_output)
#
#     def log(self, msg, log_level, color_output=True):
#         if log_level >= self.level:
#             c_msg = msg
#             if color_output:
#                 if log_level == self.LOG_INFO:
#                     c_msg = TermColor.OKBLUE + msg + TermColor.ENDC
#                 if log_level == self.LOG_WARN:
#                     c_msg = TermColor.WARNING + msg + TermColor.ENDC
#                 if log_level == self.LOG_FATAL:
#                     c_msg = TermColor.FAIL + msg + TermColor.ENDC
#                 if log_level == self.LOG_ALWAYS:
#                     c_msg = TermColor.F_DarkGray + msg + TermColor.ENDC
#             print(c_msg)


# convert string to date
# NOTE: requires format yyyy-mm-dd
def to_date(value):
    """
    convert the value passed to a date/time
    """
    if isinstance(value, str):
        return datetime.date(*(int(s) for s in value.split('-')))
    return value


def to_bool(value, keep_null=False):
    """
    convert the value passed to boolean if it meets criteria otherwise return what was passed
    NOTE: if None is passed (null) then we want to keep it since the db can support it
    """
    if value is not None:
        # note: need this line because strings and numbers are truthy and will return true
        if isinstance(value, str):
            if value.lower() in ["0", "n", "f", "false", "no"]:
                return False
        if value in [0, False]:
            return False
        if value:
            return True
        return False
    else:
        if keep_null:
            return None
        return False


def to_int(value, keep_null=False, raise_exception=False):
    """
    convert value to int where possible
    NOTE: pass keep_null=True to return None values
    NOTE: pass raise_exception to raise exceptions or it will just convert to 0 by default
    NOTE: python uses int for both ints and longs
    """
    if value is None and keep_null:
        return value
    if raise_exception:
        return int(value)
    try:
        return int(value)
    except:
        return 0


def is_true_value(value):
    if value is not None:
        if isinstance(value, str):
            if value.lower() in ["1", "y", "t", "true", "yes", "on"]:
                return True
        if value in [1, True]:
            return True
    return False


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


def namedtuplefetchall(cursor):
    "Return all rows from a cursor as a namedtuple"
    desc = cursor.description
    nt_result = namedtuple('Result', [col[0] for col in desc])
    return [nt_result(*row) for row in cursor.fetchall()]


def get_tuple_in_list(list_of_tuples, key):
    """
    returns the first tuple (key, value) for a given key in a list
    """
    for k, v in list_of_tuples:
        if k == key:
            return k, v
    return None


def get_key_by_idx(dictionary, idx=0):
    if idx < 0:
        idx += len(dictionary)
    for i, key in enumerate(dictionary.keys()):
        if i == idx:
            return key
    raise IndexError("dictionary index out of range")


def print_to_string(string):
    """
    testing printing to a string using stringio class
    """
    save_stdout = sys.stdout
    result = StringIO()
    sys.stdout = result
    print(string)
    sys.stdout = save_stdout
    return result.getvalue()


class Capture(redirect_stdout):
    """
    Class to capture the output from stdout and send to string within a block
    Ex: with capture() as message:
            print('hello world')
        print(str(message))
    """
    def __init__(self):
        self.f = io.StringIO()
        self._new_target = self.f
        self._old_targets = []  # verbatim from parent class

    def __enter__(self):
        self._old_targets.append(getattr(sys, self._stream))  # verbatim from parent class
        setattr(sys, self._stream, self._new_target)  # verbatim from parent class
        return self  # instead of self._new_target in the parent class

    def __repr__(self):
        return self.f.getvalue()


def table_exists(table_name: str, connection_name: str) -> bool:
    return table_name in connections[connection_name].introspection.table_names()


def get_table_schema(table_name: str, connection_name: str) -> dict:
    schema = {}
    if not table_exists(table_name, connection_name):
        raise IntegrityError(f"Table [{table_name}] does not exist!")

    connection = connections[connection_name]
    with connection.cursor() as cursor:
        table_info = connection.introspection.get_table_list(cursor)
    return schema


def testcapture():
    with Capture() as message:
        print('hello world')
    print(str(message))


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
