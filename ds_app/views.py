# NOTE: different drivers do callable statements differently; basing this code on mysqlclient since
#   I can't get the mysql-connector-python to tie into django 3.0.8 properly.
#   <sigh> I have always had trouble with Oracles driver; a shame really since I like the syntax better
#   and it is pure python; maybe try again later
#
# SEE: https://stackoverflow.com/questions/15320265/cannot-return-results-from-stored-procedure-using-python-cursor
#   about mid way down the page for usage differences.
#
from django.db.utils import ConnectionDoesNotExist, OperationalError
from django.http import Http404, JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import connections
from django.conf import settings
import logging
import re
import json

from .models import Endpoint
from .utils import TermColor, dictfetchall, dictfetchstoredresults, dictfetchstoredparameters
from .utils import get_key_by_idx, get_tuple_in_list, to_bool, to_int

# todo: figure out how to handle types if needed (<section_id:int>)
log = logging.getLogger("endpoint")
valid_methods = ["GET", "POST", "PUT", "DELETE"]


class SqlParameter(object):
    """
    Instead of just the arg name we need the position to know for optional arguments
    """
    def __init__(self, name, value=None, positions=(-1, -1), ordinal=False, group=None):
        self.group = group
        self.name = name
        self.start = positions[0]
        self.end = positions[1]
        self.ordinal = ordinal
        self.cast_to = None
        self.__value = value
        if ordinal:
            if group:
                # if we have a group (we should) parse the pipes if found to determine the cast_to
                # look for a |<cast char>| and perform casting on value
                # NOTE: for backwards compatibility with java strip anything we don't think we need in python
                pos_cast_start = group.find("|")
                pos_cast_end = group.rfind("|")
                if pos_cast_start > -1 and pos_cast_end > -1:
                    self.cast_to = group[pos_cast_start + 1:pos_cast_end]
        else:
            # if we have a name that is parseable like <int: name> then set cast_to and reset name
            pos_cast_delim = self.name.find(":")
            if pos_cast_delim > -1:
                self.cast_to = self.name[:pos_cast_delim]
                self.name = self.name[pos_cast_delim + 1:].strip()

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value
        if self.cast_to and self.cast_to in ["b", "bool"]:
            # cast any true, t, y, yes etc to the correct boolean value
            self.__value = to_bool(value, keep_null=True)
        if self.cast_to and self.cast_to in ["i", "l", "int"]:
            self.__value = to_int(value, keep_null=True, raise_exception=True)

    def __str__(self):
        return self.name


class MethodParameters(object):
    """
    Encapsulates the parameters passed into the url.
    """
    def __init__(self, param_list, **kwargs):
        # data structure will be a dict of keys with array of values
        self.endpoint_path = None
        self.parameters = {}
        # start by placing all kwargs that is not endpoint_path into kwvars these are path parameters defined in
        # the urls.py
        for arg, value in kwargs.items():
            # log.debug(f'kwargs -> arg: {arg} value: {value}')
            if arg == 'endpoint_path':
                self.endpoint_path = value
            else:
                self.parameters[arg] = value
        for key, value in param_list:
            # print(f'param -> key: {key} value: {value}')
            self.parameters[key] = value

    def __str__(self):
        return f'parameters: {self.parameters}'


class ParsedSql(object):
    """
    Encapsulates the state after parsing the sql
    """
    def __init__(self, sql, method_parameters):
        self.original_sql = sql
        self.uncommented_sql = self.strip_comments()
        self.params = []
        self._callable = False
        self.callable_name = ""
        self.callable_args = []
        self.init_errors = []
        self.statement = self.parse(method_parameters)

    def parse(self, method_parameters):
        """
        parses the original sql doing string replacements and building argument lists
        """
        sql = self.uncommented_sql
        # check for ? (ordinal) and add named arguments by index then just string replace
        sql = self.parse_ordinal_args(sql, method_parameters)
        # check for named parameters and add named arguments while doing string replacements
        sql = self.parse_named_args(sql)
        # next check for optional text and strip if we don't have a param
        sql = self.strip_optional_args(sql, method_parameters)
        # last set our values for our arguments by looking them up from passed parameters
        for param in self.params:
            try:
                param.value = method_parameters.parameters[param.name]
                # self.values.append(method_parameters.parameters[param])
            except KeyError:
                self.init_errors.append(f"Missing required parameter [{param}]\n")
        # if this is a callable procedure since called differently
        # mysqlclient uses the procedure name and a list of args in callproc method
        self.parse_callproc(sql)
        return sql

    def strip_comments(self):
        sql = ""
        lines = self.original_sql.split('\n')
        for line in lines:
            if line.strip().startswith("--"):
                continue
            sql += line + '\n'
        return sql

    def parse_ordinal_args(self, sql, params):
        pattern = re.compile(r'(\?(\|.\|)?)')
        new_sql = ""
        last_match = 0
        ordinal_index = 0
        for match in re.finditer(pattern, sql):
            # print(match.group(1))
            try:
                key = get_key_by_idx(params.parameters, ordinal_index)
                param = SqlParameter(key, positions=match.span(), ordinal=True, group=match.group(1))
            except IndexError:
                param = SqlParameter(f"p{ordinal_index}", positions=match.span(), ordinal=True, group=match.group(1))
            self.params.append(param)
            ordinal_index += 1
            new_sql += sql[last_match:match.start()]
            new_sql += '%s'
            last_match = match.end()
        new_sql += sql[last_match:]
        # print(f'parsed sql: {new_sql}')
        return new_sql

    def parse_named_args(self, sql):
        pattern = re.compile(r'<(.+)>')
        new_sql = ""
        last_match = 0
        for match in re.finditer(pattern, sql):
            # print(match.group(1))
            self.params.append(SqlParameter(match.group(1), positions=match.span(), group=match.group(1)))
            new_sql += sql[last_match:match.start()]
            new_sql += '%s'
            last_match = match.end()
        new_sql += sql[last_match:]
        # print(f'parsed sql: {new_sql}')
        return new_sql

    def strip_optional_args(self, sql, passed_parameters):
        us_pos_start = self.uncommented_sql.find('[')
        us_pos_end = self.uncommented_sql.rfind(']')
        s_pos_start = sql.find('[')
        s_pos_end = sql.find(']')

        if us_pos_start > -1 and us_pos_end > -1:
            missing = False
            for param in self.params:
                if param.start >= us_pos_start and param.end <= us_pos_end:
                    if param.name not in passed_parameters.parameters:
                        missing = True
                    break
            if missing:
                # remove any parameters within range (otherwise we will get the param not passed error)
                for param in reversed(self.params):
                    if param.start >= us_pos_start and param.end <= us_pos_end:
                        self.params.remove(param)
                # strip the whole block from the sql
                return sql[0:s_pos_start] + sql[s_pos_end + 1:]
            else:
                # strip only the open/close bracket tag
                return sql[0:s_pos_start] + sql[s_pos_start + 1:s_pos_end] + sql [s_pos_end + 1:]
        return sql

    def parse_callproc(self, sql):
        upper_sql = sql.upper()
        pos = upper_sql.find("CALL ")
        if pos > -1:
            pos += len("CALL ")
            pos_argstart = upper_sql.find("(", pos)
            pos_argend = upper_sql.rfind(")", pos)
            if pos > -1 and pos_argstart > -1 and pos_argend > -1:
                self._callable = True
                self.callable_name = sql[pos:pos_argstart].strip()
                self.callable_args = sql[pos_argstart + 1: pos_argend].lower().split(",")
                # substitute any callable args '%s' with the next value
                value_idx = 0
                for arg_idx in range(len(self.callable_args)):
                    # if self.callable_args[arg_idx] and self.callable_args[arg_idx].strip().startswith("%s"):
                    if self.callable_args[arg_idx] and self.callable_args[arg_idx].strip() == "%s":
                        if len(self.params) > arg_idx:
                            self.callable_args[arg_idx] = self.params[value_idx].value
                            value_idx += 1
            log.debug(f"callable_name:\n{self.callable_name}")
            log.debug(f"callable_args:\n{self.callable_args}")

    def is_update(self):
        pos_update = self.statement.lower().find("update")
        if pos_update <= -1:
            return False
        pos_select = self.statement.lower().find("select")
        if pos_select > -1 and pos_select < pos_update:
            return False
        return True

    def is_callable(self):
        return self._callable

    def parameter_names(self):
        """
        returns the sql parameter names in a list for use in sql calls
        """
        name_list = []
        for param in self.params:
            name_list.append(param.name)
        return name_list

    def parameter_values(self):
        """
        returns the sql parameter values in a list for use in sql calls
        """
        value_list = []
        for param in self.params:
            value_list.append(param.value)
        return value_list

    def __str__(self):
        return self.statement


class ExecutableStatement(object):
    """
    Encapsulates the data and logic for exectuing a statement saved in the database and caching the results
    supports sql, parameterized sql and callable statements
    returns array of dict results or a wrappered array of dict results with other parameters
    debug can be passed as kwarg to add debug properties to the result set
    NOTE: sql can be named args or ?
    """
    def __init__(self, connection_name, sql, param_list, **kwargs):
        self.connection_name = connection_name
        self.method_parameters = MethodParameters(param_list, **kwargs)
        self.sql = ParsedSql(sql, self.method_parameters)
        self.updated_recs = 0
        self.results = []
        self.wrappered_results = {}

    def execute(self):
        # log.debug(f'trying to open connection [{self.connection_name}]')
        with connections[self.connection_name].cursor() as cursor:
            # NOTE: I am not sure why I wrappered everything for this error, however
            #   it prevents SQL Errors from showing so I need to raise it for now;
            #   maybe for callable statement?  test this out for both params and results
            try:
                if self.sql.is_callable():
                    self.wrappered_results['cs'] = 'true'
                    cursor.callproc(self.sql.callable_name, self.sql.callable_args)
                    self.updated_recs = cursor.rowcount
                    self.wrappered_results['updated'] = self.updated_recs
                    self.wrappered_results['parameters'] = dictfetchstoredparameters(cursor, self.sql.callable_name, self.sql.callable_args)
                    self.results = dictfetchstoredresults(cursor)
                    self.wrappered_results['resultsets'] = self.results
                else:
                    if self.sql.params:
                        cursor.execute(self.sql.statement, self.sql.parameter_values())
                    else:
                        cursor.execute(self.sql.statement)
                    self.results = dictfetchall(cursor)
                    self.updated_recs = cursor.rowcount
            except OperationalError as oe:
                log.debug(oe)
                if settings.DEBUG:
                    raise oe

    def get_json_response(self):
        # todo: add logic for wrappering with debug properties
        if self.sql.is_callable():
            # add to wrappered_results if debug later
            return JsonResponse(self.wrappered_results, safe=False)
        else:
            # change to wrappered_results if debug later
            if self.sql.is_update():
                return JsonResponse(f'{{"updated":{self.updated_recs}}}')
            else:
                return JsonResponse(self.results, safe=False)


@csrf_exempt
def process_endpoint(request, *args, **kwargs):
    """
    Processes the endpoint and returns the results if there is a match in urls.py

    :param request: the request object
    :param args: any non named arguments passed to the request
    :param kwargs: any keyword arguments passed to the request
    :return: json response or raised exception
    """
    original_log_level = log.level
    _endpoint_path = kwargs.get("endpoint_path")
    _connection_name = ""
    try:
        endpoint = Endpoint.objects.get(path=_endpoint_path)
        if endpoint.is_disabled:
            raise Http404("API disabled")

        # we have our endpoint and not disabled so lets execute our query and return the results as json
        _connection_name = endpoint.connection_name or ""
        _connection_name = _connection_name.strip()
        _method = request.method
        _param_list = []
        if request.META.get('CONTENT_TYPE') and 'json' in request.META.get('CONTENT_TYPE').lower() and request.body:
            received_json_data = json.loads(request.body)
            _param_list = list(received_json_data.items())
        if _method.upper() == "POST":
            _param_list += list(request.POST.items())
            if request.POST.get("method"):
                if request.POST.get("method").upper().strip() in valid_methods:
                    _method = request.POST.get("method").upper().strip()
        else:
            _param_list += list(request.GET.items())
            if request.GET.get("method") and request.GET.get("method").upper().strip() in valid_methods:
                _method = request.GET.get("method").upper().strip()

        # override logging as early as possible if set (need params)
        if endpoint.log_level_override:
            log.setLevel(endpoint.log_level_override)
            # we use the adapter to add a skip attribute to the logrecord and then filter if needed

            requested_value = None
            param_value = None
            if endpoint.log_filter_field_name:
                log_extra = {'skip': True}
                if endpoint.log_filter_field_value is None:
                    requested_value = ""
                else:
                    requested_value = str(endpoint.log_filter_field_value)
                param_tuple = get_tuple_in_list(_param_list, endpoint.log_filter_field_name)
                if param_tuple:
                    if param_tuple[1] is None:
                        param_value = ""
                    else:
                        param_value = str(param_tuple[1])
                    if param_value == requested_value:
                        log_extra = {'skip': False}
            else:
                log_extra = {'skip': False}
            logex = logging.LoggerAdapter(log, extra=log_extra)
            logex.info(
                f"{TermColor.BOLD}{TermColor.UNDERLINE}------- endpoint: {_endpoint_path} --------{TermColor.ENDC}")
            logex.debug(f'filter value: {str(requested_value)}')
            logex.debug(f'param value: {str(param_value)}')
            logex.debug(f'log extra: {str(log_extra)}')
        else:
            logex = log
            logex.info(
                f"{TermColor.BOLD}------- endpoint: {_endpoint_path} --------{TermColor.ENDC}")
        logex.debug(f'path: {request.path}')
        logex.debug(f'args: {args}')
        logex.debug(f'kwargs: {kwargs}')
        logex.debug(f'original log level: {original_log_level}')
        logex.debug(f'overridden log level: {log.level}')
        logex.debug(f"method: {_method}")
        logex.debug(f"content type: {request.META.get('CONTENT_TYPE')}")
        logex.debug(f'body data: {str(request.body)}')
        # info print out our params for every call
        for key, value in _param_list:
            logex.info(f"     {TermColor.F_DarkGray}{key}: {value}{TermColor.ENDC}")
        property_name = _method.lower() + "_statement"
        logex.debug(f"getting property: {property_name}")
        sql = getattr(endpoint, property_name)
        logex.debug(f"sql: {sql}")
        statement = ExecutableStatement(_connection_name, sql, _param_list, **kwargs)
        logex.debug(f'statement parsed sql: {str(statement.sql).strip()}')
        logex.debug(f'statement parameters: {str(statement.sql.parameter_names())}')
        logex.debug(f'statement values: {str(statement.sql.parameter_values())}')
        logex.debug(f'passed parameters: {statement.method_parameters.parameters}')
        if statement.sql.init_errors:
            log.setLevel(original_log_level)
            return HttpResponseBadRequest(statement.sql.init_errors)

        statement.execute()
        json_response = statement.get_json_response()
        logex.debug(f'response[{str(json_response.status_code)}]: {str(json_response.content)}')
        logex.info(
            f"{TermColor.BOLD}{TermColor.UNDERLINE}------- endpoint: {_endpoint_path} --------{TermColor.ENDC}")
        log.setLevel(original_log_level)
        return json_response

    except Endpoint.DoesNotExist as dneerr:
        _msg = f'ERROR: we tried to get endpoint for [{_endpoint_path}] but it was not found!\n{dneerr}'
        print(_msg)
        log.setLevel(original_log_level)
        if settings.DEBUG:
            raise Http404(_msg)
        else:
            raise Http404("API not found")
    except ConnectionDoesNotExist as conerr:
        _msg = f'ERROR: Unable to get connection [{_connection_name}] for endpoint [{_endpoint_path}]\n{conerr}'
        print(_msg)
        log.setLevel(original_log_level)
        if settings.DEBUG:
            raise Http404(_msg)
        else:
            raise Http404("Unable to connect to the database")
    finally:
        log.setLevel(original_log_level)
