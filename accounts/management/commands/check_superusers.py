from django.core.management.base import BaseCommand
from accounts.models import CustomUser

class Command(BaseCommand):
    help = 'スーパーユーザーアカウントの状態を確認します。'

    def handle(self, *args, **options):
        superusers = CustomUser.objects.filter(is_superuser=True)
        if not superusers.exists():
            self.stdout.write(self.style.WARNING('スーパーユーザーが見つかりません。'))
            return

        self.stdout.write(self.style.SUCCESS('スーパーユーザーアカウント状態:'))
        for user in superusers:
            self.stdout.write(f'  - Username: {user.username}')
            self.stdout.write(f'    is_staff: {user.is_staff}')
            self.stdout.write(f'    role: {user.role}')
            if not user.is_staff:
                self.stdout.write(self.style.ERROR('    ^ このユーザーは管理サイト(/admin/)にログインできない可能性があります。'))
