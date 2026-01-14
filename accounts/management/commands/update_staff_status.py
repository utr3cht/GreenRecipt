from django.core.management.base import BaseCommand
from accounts.models import CustomUser

class Command(BaseCommand):
    help = '役割に基づいて全ユーザーのis_staffステータスを更新します。'

    def handle(self, *args, **options):
        updated_count = 0
        users = CustomUser.objects.all()
        for user in users:
            new_is_staff = user.role in ['admin', 'system', 'store']
            if user.is_staff != new_is_staff:
                user.is_staff = new_is_staff
                user.save(update_fields=['is_staff'])
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'ユーザー {user.username} を更新しました'))
        
        self.stdout.write(self.style.SUCCESS(f'{updated_count} 人のユーザーを正常に更新しました。'))