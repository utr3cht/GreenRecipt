from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Count

class Command(BaseCommand):
    help = 'CustomUserモデル内の重複メールアドレスを検索し報告します。'

    def handle(self, *args, **options):
        User = get_user_model
        # 重複メール検索
        duplicates = User.objects.values('email') \
            .annotate(email_count=Count('email')) \
            .filter(email_count__gt=1, email__isnull=False)

        if duplicates.exists():
            self.stdout.write(self.style.WARNING('重複したメールアドレスが見つかりました:'))
            for item in duplicates:
                email = item['email']
                count = item['email_count']
                self.stdout.write(f'- Email: {email}, Count: {count}')
                users_with_duplicate_email = User.objects.filter(email=email)
                for user in users_with_duplicate_email:
                    self.stdout.write(f'  - User ID: {user.id}, Username: {user.username}')
        else:
            self.stdout.write(self.style.SUCCESS('重複したメールアドレスは見つかりませんでした。'))

        # NULLメールユーザーの確認
        null_emails = User.objects.filter(email__isnull=True)
        if null_emails.exists():
            self.stdout.write(self.style.WARNING('メールアドレスがNULLのユーザーが見つかりました:'))
            for user in null_emails:
                self.stdout.write(f'- User ID: {user.id}, Username: {user.username}')
        else:
            self.stdout.write(self.style.SUCCESS('メールアドレスがNULLのユーザーは見つかりませんでした。'))
