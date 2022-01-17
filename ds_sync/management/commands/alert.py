from django.core.management.base import BaseCommand
from argparse import RawTextHelpFormatter
from ds_sync.models import *


class Command(BaseCommand):
    filter = None

    help = """
        usage: ./manage.py alert [category]
        --------------------------------------
        example: ./manage.py [? -h --help]  
            display this help message
        example: ./manage.py alert
            process all active alerts without a category
        example: ./manage.py alert weekly 
            process all active alerts for given category
        
    """

    def alert(self):
        log_msg = ""
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
            if len(params) >= 1:
                self.filter = params[0]
            self.stdout.write(self.style.SUCCESS(f'filter: {str(self.filter)}'))
            self.stdout.write(self.style.SUCCESS(self.alert()))
