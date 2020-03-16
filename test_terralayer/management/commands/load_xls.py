from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Dump a layer to json format"

    def add_arguments(self, parser):
        parser.add_argument(
            "--scene-name", "-s", action="store", help="Scene name", required=True
        )
        parser.add_argument(
            "--file", "-f", action="store", help="File to load", required=True
        )

    def handle(self, *args, **options):
        print("Fake load xls command...")
