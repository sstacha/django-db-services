import datetime
from django.utils import timezone

from django.core.management.base import BaseCommand
from argparse import RawTextHelpFormatter
from django.db import IntegrityError, connections
import logging
from ds_app.utils import table_exists, LogBuffer, to_bool, dictfetchall, namedtuplefetchall


from ds_sync.models import *

# log = logging.getLogger(__name__)
logger = logging.getLogger(__name__)


def validate_config(config: SyncConfiguration) -> None:
    validation_errors = []
    if not table_exists(config.table_name, config.from_connection_name):
        validation_errors.append(
            f"Source table [{str(config.from_connection_name)}]:[{str(config.table_name)}] not found!")
    if not table_exists(config.table_name, config.to_connection_name):
        validation_errors.append(
            f"Target table [{str(config.to_connection_name)}]:[{str(config.table_name)}] not found!")
    with connections[config.from_connection_name].cursor() as from_cursor:
        from_cursor.execute(f"select * from {config.table_name}")
        columns = [col[0] for col in from_cursor.description]
        if config.pk_field_name not in columns:
            validation_errors.append(
                f"PK field [{config.pk_field_name}] does not exist in source table ["
                f"{str(config.from_connection_name)}]:[{str(config.table_name)}]!"
            )
    if validation_errors:
        raise IntegrityError("\n".join(validation_errors))


# def sync_config_old(log, config: SyncConfiguration) -> SyncRun:
#     log.warning(f"syncing {str(config)}...")
#     run = None
#     # validate the config
#     validate_config(config)
#     # skip if there is a process still running for this config
#     running = SyncRun.objects.filter(sync=config, end_date__isnull=True)
#     if len(running) > 0:
#         log.warning(f"[{str(config)}] has not completed; skipping run!")
#         return run
#     # create a configuration run and process
#     run = SyncRun.objects.create(sync=config)
#     log.debug(f"created {str(run)}")
#     return run
def is_dirty(from_result, to_result):
    if not to_result:
        return True
    from_value_list = list(from_result)
    to_value_list = list(to_result)
    for idx, value in enumerate(from_value_list):
        if to_value_list[idx] != value:
            return True
    return False


def sync_config(log: LogBuffer, config: SyncConfiguration) -> None:
    log.info(f"syncing {str(config)}...")
    # validate the config
    validate_config(config)
    # skip if there is a process still running for this config
    # NOTE: we will always have one open for this run so look for > 1
    running = SyncRun.objects.filter(sync=config, end_date__isnull=True)
    if len(running) > 1:
        log.warning(f"[{str(config)}] has not completed; skipping run!")
        return None
    # pull the data from the source connection
    query_sql = f"select * from {config.table_name}"
    pk_where = f" where {config.pk_field_name}=%s"
    updated_total = 0
    with connections[config.from_connection_name].cursor() as from_cursor:
        from_cursor.execute(query_sql)
        from_results = namedtuplefetchall(from_cursor)
        with connections[config.to_connection_name].cursor() as to_cursor:
            for from_result in from_results:
                log.debug(f"from: {str(from_result)}")
                to_cursor.execute(query_sql + pk_where, [getattr(from_result, config.pk_field_name)])
                to_results = namedtuplefetchall(to_cursor)
                if len(to_results) > 0:
                    # update to record since it exists
                    to_result = to_results[0]
                    log.debug(f"to: {str(to_result)}")
                    if is_dirty(from_result, to_result):
                        log.debug(f"updating...")
                        field_list = from_result._fields
                        value_list = list(from_result)
                        update_field_list = []
                        for field in field_list:
                            update_field_list.append(str(field) + "=%s")
                        # log.debug(f"update field list: {update_field_list}")
                        update_sql = f"update {config.table_name} set {', '.join(update_field_list)} {pk_where}"
                        log.debug(f"update sql: {update_sql}")
                        value_list.append(getattr(from_result, config.pk_field_name))
                        to_cursor.execute(update_sql, value_list)
                        updated_recs = to_cursor.rowcount
                        updated_total += updated_recs
                        log.debug(f"updated recs: {updated_recs}")
                    else:
                        log.debug("not dirty. skipping...")
                        log.debug(f"updated recs: 0")
                else:
                    # add to record since it doesn't exist
                    log.debug(f"adding...")
                    # get our fields from the named tuple
                    field_list = from_result._fields
                    field_list_str = ", ".join(field_list)
                    # our value list is %s for each value which we will pass as params on execute
                    rng = range(len(from_result))
                    # value_list = ["{:02d}".format(x) for x in rng]
                    value_list = ["%s" for x in rng]
                    log.debug(f"value list: {value_list}")
                    value_list_str = ", ".join(value_list)
                    log.debug(f"value list str: {value_list_str}")
                    insert_sql = f"insert into {config.table_name} ({field_list_str}) values ({value_list_str})"
                    log.debug(f"insert sql: \n {insert_sql}")
                    value_params = list(from_result)
                    log.debug(f"value_params: {value_params}")
                    to_cursor.execute(insert_sql, value_params)
                    updated_recs = to_cursor.rowcount
                    updated_total += updated_recs
                    log.debug(f"updated recs: {updated_recs}")
    log.info(f"total updated recs: {updated_total}")


class Command(BaseCommand):
    filter_type = "table"
    filter = None
    color = None

    help = """
        usage: ./manage.py sync [option] [parameter]
        --------------------------------------
        options:
            ? or help - display this help message
            channel [<channel_name>] - syncs all configurations; if channel_name is passed will filter to that channel.
                configurations
            table <table_name> - syncs all active configurations for specified table.  warning issued if not found.
            alerts [<category>] - syncs all active alerts; if category is passed will filter to that category.
            
        example: ./manage.py sync [? help]
            display this help message
        example: ./manage.py sync channel
            process all active sync configurations that does not have a channel selected
        example: ./manage.py sync channel crm/customer
            process all active sync configurations with the specified channel
        example: ./manage.py sync table 
            process all active sync configurations
        example: ./manage.py sync table crm_awards
            process all active sync configurations for the given table
        NOTE: warns if no active configurations exist for the table
        example: ./manage.py sync alert
            process all active alerts
        example: ./manage.py sync alert weekly
            process all active alerts with the weekly category
    """

    def sync_configurations(self):
        """
        sync configurations optionally filtering to a passed table or channel
        """
        log = LogBuffer(logger=logger, color_output=self.color)
        log.debug(f"system log level: {logger.getEffectiveLevel()}")
        log.debug(f"buffer log level: {log.level}")
        run_log_prefix = ""
        run_log_summary = ""
        run_log = LogBuffer(logger=logger, color_output=self.color)
        try:
            run_log.debug(f"syncing configurations for {str(self.filter_type)} [{str(self.filter)}]")
            # get our list of configs to sync depending on table or channel
            if self.filter:
                if self.filter_type == 'table':
                    configs = SyncConfiguration.objects.active().filter(table_name__iexact=self.filter)
                    disabled_configs = SyncConfiguration.objects.disabled().filter(table_name__iexact=self.filter)
                else:
                    configs = SyncConfiguration.objects.active().filter(channels__name__in=self.filter)
                    disabled_configs = SyncConfiguration.objects.disabled().filter(channels__name__in=self.filter)
            else:
                if self.filter_type == 'table':
                    configs = SyncConfiguration.objects.active().all()
                    disabled_configs = SyncConfiguration.objects.disabled().all()
                else:
                    configs = SyncConfiguration.objects.active().filter(channels__isnull=True)
                    disabled_configs = SyncConfiguration.objects.disabled().filter(channels__isnull=True)
            # always log our disabled configs as warnings so we know when troubleshooting
            if disabled_configs:
                run_log.warning(f"[{len(disabled_configs)}] inactive configurations")
                for disabled_config in disabled_configs:
                    run_log.warning(f"     {str(disabled_config)}")
            run_log.debug(f"[{len(configs)}] configurations")
            run_log_prefix += str(run_log)
            run_log_summary += str(run_log)
            # for each active config reset and sync
            # NOTE: there will be a run for each table synced for logging and errors
            for config in configs:
                # NOTE: clear also resets the log level to initial value (see LogBuffer)
                run_log.clear()
                if config.log_level_override and config.log_level_override != run_log.level:
                    run_log.debug(f"config: {str(config)}")
                    run_log.debug(f"overriding run log level from [{run_log.level}] to [{str(config.log_level_override)}]")
                    run_log.level = config.log_level_override
                # create a configuration run and process
                run = SyncRun.objects.create(sync=config)
                log.debug(f"created {str(run)}")
                try:
                    sync_config(run_log, config)
                    run.has_succeeded = True
                except Exception as run_ex:
                    run_log.fatal(run_ex)
                    run.has_succeeded = False
                finally:
                    run.log = run_log_prefix + str(run_log)
                    run.end_date = timezone.now()
                    run.save()
                    run_log_summary += str(run_log)
            log.always(run_log_summary)

        except Exception as ex:
            log.log("", LogBuffer.LOG_SPACE)
            log.fatal(f"\n---------------------------\n{run_log_summary}")
            log.fatal(f"{str(ex)}")
            log.fatal(f"\n---------------------------\n")

        log.warning("warning")
        log.debug("debug")
        log.info("info")
        log.fatal("fatal")

        return str(log)

    def sync_alerts(self):
        log_msg = "syncing alerts..."
        return log_msg

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument('option', nargs='+', type=str)

    def handle(self, *args, **options):
        params = options['option']
        if "?" in params or "help" in params:
            self.stdout.write(self.style.SUCCESS(self.help))
        else:
            if len(params) >= 2:
                if len(params[1]) > 0:
                    self.filter = params[1]
            if len(params) >= 3:
                if len(params[2]) > 0:
                    self.color = to_bool(params[2])
            self.stdout.write(self.style.SUCCESS(f'filter: {str(self.filter)}'))
            if "channel" in params:
                self.filter_type = 'channel'
                # split the channels into a list since it uses in sql
                if self.filter:
                    self.filter = self.filter.split(',')
                else:
                    self.stdout.write(self.style.WARNING(
                        "No channel was passed; syncing all configurations without an assigned channel!"))
                self.stdout.write(self.style.SUCCESS(self.sync_configurations()))
            elif "table" in params:
                self.filter_type = 'table'
                self.stdout.write(self.sync_configurations())
            elif "alerts" in params:
                self.stdout.write(self.style.SUCCESS(self.sync_alerts()))
            else:
                self.stderr.write(self.style.ERROR(f"Invalid option [{params[0]}]"))
                self.stderr.write(self.style.ERROR(self.help))
