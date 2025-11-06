from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Checks the schema of the accounts_customuser table.'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(accounts_customuser);")
            columns = cursor.fetchall()

        if not columns:
            self.stdout.write(self.style.ERROR('Table accounts_customuser not found or has no columns.'))
            return

        self.stdout.write(self.style.SUCCESS('--- Schema for accounts_customuser ---'))
        for col in columns:
            self.stdout.write(f'Name: {col[1]}, Type: {col[2]}, Not Null: {bool(col[3])}, Default: {col[4]}, PK: {bool(col[5])}')
        self.stdout.write(self.style.SUCCESS('--------------------------------------'))
