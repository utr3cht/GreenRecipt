from django.core.management.base import BaseCommand
from accounts.models import CustomUser

class Command(BaseCommand):
    help = 'Updates the is_staff status for all users based on their role.'

    def handle(self, *args, **options):
        updated_count = 0
        users = CustomUser.objects.all()
        for user in users:
            new_is_staff = user.role in ['admin', 'system']
            if user.is_staff != new_is_staff:
                user.is_staff = new_is_staff
                user.save(update_fields=['is_staff'])
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'Updated user {user.username}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} users.'))
