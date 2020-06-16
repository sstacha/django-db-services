from django.db.utils import ConnectionDoesNotExist, OperationalError
from django.http import Http404, JsonResponse
from django.db import connections
from django.conf import settings
import logging
import re

from .models import Endpoint
from .utils import TermColor, dictfetchall, dictfetchstoredresults

# todo: figure out how to handle types if needed (<section_id:int>)
log = logging.getLogger("ds_app")
valid_methods = ["GET", "POST", "PUT", "DELETE"]


class ExecutableStatement(object):
    """
    Encapsulates the data and logic for exectuing a statement saved in the database and caching the results
    supports sql, parameterized sql and callable statements
    returns array of dict results or a wrappered array of dict results with other parameters
    debug can be passed as kwarg to add debug properties to the result set
    """
    def __init__(self, connection_name, sql, param_list, **kwargs):
        self.connection_name = connection_name
        self.original_sql = sql
        self.sql = sql
        self.param_list = param_list
        self.kwargs = kwargs
        # initialize our parameter values with the kwargs values
        # NOTE: these will be named but the sql could be ordered ? or named <id>
        self.kwvars = {}
        self.ordinal_values = self.get_ordinal_values(**kwargs)
        self.is_callable = False
        self.is_update = False
        self.updated_recs = 0
        self.results = []
        self.wrappered_results = {}

    def get_ordinal_values(self, **kwargs):
        values = []
        sql = ""
        # strip all comments
        lines = self.original_sql.split('\n')
        for line in lines:
            if line.strip().startswith("--"):
                continue
            sql += line + "\n"
        # check for ? (ordinal) if found check the number of kwargs is >= number of ?
        parts = sql.split("?")
        param_count = len(parts) - 1
        if param_count:
            # start by placing all kwargs that is not endpoint_path into kwvars these are path parameters defined in
            # the urls.py
            # NOTE: since we don't have named parameters just questionmarks we must assume every arg except
            #   endpoint_path is done by the definition and we need it
            for arg, value in kwargs.items():
                # log.debug(f'kwargs -> arg: {arg} value: {value}')
                if arg != 'endpoint_path':
                    self.kwvars[arg] = value
            # log.debug(f'kwvars: {self.kwvars}')
            # add the kwvars to our ordinal value list
            for arg, value in self.kwvars.items():
                # print(f'kwvars -> arg: {arg} value: {value}')
                values.append(value)
                if len(values) == param_count:
                    break
            # replace any ? with %s (needed for python lib to execute correctly)
            self.sql = sql.replace("?", "%s")
            # add any get/post values in order until we get the max number of ordinal value replacements needed
            if len(values) < param_count:
                # add the remaining kwvars/values with GET/POST params that are passed as param_list
                for key, value in self.param_list:
                    # print(f'param -> key: {key} value: {value}')
                    self.kwvars[key] = value
                    values.append(value)
                    if len(values) == param_count:
                        break
            log.debug(f"kwvars: {self.kwvars}")
            log.debug(f"ordinal values: {values}")
            # if we don't have the right number of params raise exception since sql will fail anyway
            if len(values) != param_count:
                err_msg = f"Expected [{param_count}] values in sql but only found [{len(values)}]"
                err_msg += f"original_sql: {self.original_sql}\n"
                err_msg += f"sql: {self.sql}\n"
                err_msg += f"kwvars: {self.kwvars}\n"
                raise Exception(err_msg)
        else:
            # by value is a bit different we want to loop through each variable and set the values by looking for
            #   the value by name in both kwargs and params.  If no value matches we error.  We get the values
            #   list by getting the list of values from the kwvars which should be ordered.
            new_string = ""
            pattern = re.compile(r'<(\S+)>')
            last_match = 0
            for match in re.finditer(pattern, sql):
                # print(match.group(1))
                self.kwvars[match.group(1)] = None
                new_string += sql[last_match:match.start()]
                new_string += '%s'
                last_match = match.end()
            new_string += sql[last_match:]
            # print(f'new string: {new_string}')
            self.sql = new_string
            # print(f'sql: {self.sql}')
            # print(f'kwvars: {self.kwvars}')
            # for each kwvar defined in the statement look for the value and throw an exception if not found somewhere
            for key in self.kwvars:
                # print(key)
                # try to get the kwvars item for this key
                value = kwargs.get(key)
                if not value:
                    value = self.param_list.get(key)
                self.kwvars[key] = value
            log.debug(f'kwvars: {self.kwvars}')
            # todo: add code to look and adjust sql for optional parameters instead of just raising the error
            values = list(self.kwvars.values())
            log.debug(f'ordinal values: {values}')
            for key, value in self.kwvars.items():
                if value is None:
                    err_msg = f"Expected value for [{key}] but did not find in path or parameter\n"
                    err_msg += f"original_sql: {self.original_sql}\n"
                    err_msg += f"sql: {self.sql}\n"
                    err_msg += f"kwvars: {self.kwvars}\n"
                    raise Exception(err_msg)
        return values

    def execute(self):
        log.debug(f'trying to open connection [{self.connection_name}]')
        with connections[self.connection_name].cursor() as cursor:
            if self.is_callable:
                if self.is_update:
                    self.wrappered_results['result_args'] = cursor.callproc(self.sql, self.ordinal_values)
                else:
                    self.wrappered_results['result_args'] = cursor.callproc(self.sql)
                self.results = dictfetchstoredresults(cursor)
                self.wrappered_results['results'] = self.results
                self.updated_recs = len(self.results)
            else:
                try:
                    if self.ordinal_values:
                        cursor.execute(self.sql, self.ordinal_values)
                    else:
                        cursor.execute(self.sql)
                    self.results = dictfetchall(cursor)
                    self.updated_recs = cursor.rowcount
                except OperationalError as oe:
                    log.debug(oe)

    def get_json_repsonse(self):
        # todo: add logic for wrappering with debug properties
        if self.is_update:
            return JsonResponse(f'{{"updated":{self.updated_recs}}}')
        else:
            if self.is_callable:
                return JsonResponse(self.wrappered_results, safe=False)
            else:
                # change to wrappered_results if debug later
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
        log.debug(f'statement.sql: {str(statement.sql).strip()}')
        log.debug(f'statement.ordinal_values: {statement.ordinal_values}')
        statement.execute()
        log.info(
            TermColor.BOLD + TermColor.UNDERLINE + '------- endpoint: ' + _endpoint_path + ' --------' + TermColor.ENDC)
        return statement.get_json_repsonse()

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


# HOW TO IMPLEMENT PREPARED STATEMENT
    #     if not self.name in self.get_prepared().keys()
    #        # Statement will be prepared once per session.
    #        self.prepare()
    #
    #     SQL = "EXECUTE %s " % self.name
    #
    #     if self.vars:
    #         missing_vars = set(self.vars) - set(kwvars)
    #         if missing_vars:
    #             raise TypeError("Prepared Statement %s requires variables: %s" % (
    #                                 self.name, ", ".join(missing_variables) ) )
    #
    #         param_list = [ var + "=%s" for var in self.vars ]
    #         param_vals = [ kwvars[var] for var in self.vars ]
    #
    #         SQL += "USING " + ", ".join( param_list )
    #
    #         return self.__executeQuery(SQL, *param_vals)
    #     else:
    #         return self.__executeQuery(SQL)
    #
    # def __executeQuery(self,query, *args):
    #     cursor = connection.cursor()
    #     if args:
    #         cursor.execute(query,args)
    #     else:
    #         cursor.execute(query)
    #     return cursor
