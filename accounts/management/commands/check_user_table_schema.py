from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'accounts_customuserテーブルのスキーマを確認します。'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(accounts_customuser);")
            columns = cursor.fetchall()

        if not columns:
            self.stdout.write(self.style.ERROR('テーブル accounts_customuser が見つからないか、カラムがありません。'))
            return

        self.stdout.write(self.style.SUCCESS('--- accounts_customuser スキーマ ---'))
        for col in columns:
            self.stdout.write(f'Name: {col[1]}, Type: {col[2]}, Not Null: {bool(col[3])}, Default: {col[4]}, PK: {bool(col[5])}')
        self.stdout.write(self.style.SUCCESS('--------------------------------------'))
