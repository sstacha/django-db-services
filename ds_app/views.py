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
from django.db import connections
from django.conf import settings
import logging
import re

from .models import Endpoint
from .utils import TermColor, dictfetchall, dictfetchstoredresults, dictfetchstoredparameters, get_key_by_idx

# todo: figure out how to handle types if needed (<section_id:int>)
log = logging.getLogger("ds_app")
valid_methods = ["GET", "POST", "PUT", "DELETE"]


class SqlParameter(object):
    """
    Instead of just the arg name we need the position to know for optional arguments
    """
    def __init__(self, name, value=None, positions=(-1, -1)):
        self.name = name
        self.value = value
        self.start = positions[0]
        self.end = positions[1]

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
        pattern = re.compile(r'(\?)')
        new_sql = ""
        last_match = 0
        ordinal_index = 0
        for match in re.finditer(pattern, sql):
            # print(match.group(1))
            try:
                param = SqlParameter(get_key_by_idx(params.parameters, ordinal_index), positions=match.span())
            except IndexError:
                param = SqlParameter(f"p{ordinal_index}", positions=match.span())
            self.params.append(param)
            ordinal_index += 1
            new_sql += sql[last_match:match.start()]
            new_sql += '%s'
            last_match = match.end()
        new_sql += sql[last_match:]
        # print(f'parsed sql: {new_sql}')
        return new_sql

    def parse_named_args(self, sql):
        pattern = re.compile(r'<(\S+)>')
        new_sql = ""
        last_match = 0
        for match in re.finditer(pattern, sql):
            # print(match.group(1))
            self.params.append(SqlParameter(match.group(1), positions=match.span()))
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
        pos = upper_sql.find("CALLPROC")
        if pos > -1:
            pos += len("CALLPROC")
            pos_argstart = upper_sql.find("(", pos)
            pos_argend = upper_sql.rfind(")", pos)
            if pos > -1 and pos_argstart > -1 and pos_argend > -1:
                self._callable = True
                self.callable_name = sql[pos:pos_argstart].strip()
                self.callable_args = sql[pos_argstart + 1: pos_argend].split(",")
                # substitute any callable args '%s' with the next value
                value_idx = 0
                for arg_idx in range(len(self.callable_args)):
                    if self.callable_args[arg_idx] == "%s":
                        if len(self.params) - 1 >= arg_idx:
                            self.callable_args[arg_idx] = self.params[value_idx].value
                            value_idx += 1
            # print(f"callable_name:\n{self.callable_name}")
            # print(f"callable_args:\n{self.callable_args}")

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
        log.debug(f'trying to open connection [{self.connection_name}]')
        with connections[self.connection_name].cursor() as cursor:
            try:
                if self.sql.is_callable():
                    cursor.callproc(self.sql.callable_name, self.sql.callable_args)
                    self.updated_recs = cursor.rowcount
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

    def get_json_response(self):
        # todo: add logic for wrappering with debug properties
        if self.sql.is_callable():
            # add to wrappered_results if debug later
            if self.sql.is_update():
                self.wrappered_results['updated'] = self.updated_recs
            return JsonResponse(self.wrappered_results, safe=False)
        else:
            # change to wrappered_results if debug later
            if self.sql.is_update():
                return JsonResponse(f'{{"updated":{self.updated_recs}}}')
            else:
                return JsonResponse(self.results, safe=False)


def process_endpoint(request, *args, **kwargs):
    """
    Processes the endpoint and returns the results if there is a match in urls.py

    :param request: the request object
    :param args: any non named arguments passed to the request
    :param kwargs: any keyword arguments passed to the request
    :return: json response or raised exception
    """
    # generically process any request that matches a defined path endpoint from the admin
    _endpoint_path = kwargs.get("endpoint_path")
    log.info(
        TermColor.BOLD + TermColor.UNDERLINE + '------- endpoint: ' + _endpoint_path + ' --------' + TermColor.ENDC)
    log.debug('processing endpoint...')
    log.debug(f'path: {request.path}')
    # print(kwargs.get('id'))
    log.debug(f'args: {args}')
    log.debug(f'kwargs: {kwargs}')
    # for kwarg_key, kwarg_value in kwargs.items():
    #     log.debug(f'kwarg: [{kwarg_key}] {kwarg_value}')
    # print(f'ds_path: {_endpoint_path}')
    # since we use the path to get called we know it exists
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
        log.debug(f"method: {_method}")
        if _method.upper() == "POST":
            _param_list = list(request.POST.items())
            if request.POST.get("method"):
                if request.POST.get("method").upper().strip() in valid_methods:
                    _method = request.POST.get("method").upper().strip()
        else:
            _param_list = list(request.GET.items())
            if request.GET.get("method") and request.GET.get("method").upper().strip() in valid_methods:
                _method = request.GET.get("method").upper().strip()
        property_name = _method.lower() + "_statement"
        log.debug(f"getting property: {property_name}")
        sql = getattr(endpoint, property_name)
        log.debug(f"sql: {sql}")
        statement = ExecutableStatement(_connection_name, sql, _param_list, **kwargs)
        log.debug(f'statement parsed sql: {str(statement.sql).strip()}')
        log.debug(f'statement parameters: {str(statement.sql.parameter_names())}')
        log.debug(f'statement values: {str(statement.sql.parameter_values())}')
        log.debug(f'passed parameters: {statement.method_parameters.parameters}')
        if statement.sql.init_errors:
            return HttpResponseBadRequest(statement.sql.init_errors)
        statement.execute()
        log.info(
            TermColor.BOLD + TermColor.UNDERLINE + '------- endpoint: ' + _endpoint_path + ' --------' + TermColor.ENDC)
        return statement.get_json_response()

    except Endpoint.DoesNotExist as dneerr:
        _msg = f'ERROR: we tried to get endpoint for [{_endpoint_path}] but it was not found!\n{dneerr}'
        print(_msg)
        if settings.DEBUG:
            raise Http404(_msg)
        else:
            raise Http404("API not found")
    except ConnectionDoesNotExist as conerr:
        _msg = f'ERROR: Unable to get connection [{_connection_name}] for endpoint [{_endpoint_path}]\n{conerr}'
        print(_msg)
        if settings.DEBUG:
            raise Http404(_msg)
        else:
            raise Http404("Unable to connect to the database")
