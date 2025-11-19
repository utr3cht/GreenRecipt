from django.core.management.base import BaseCommand
from accounts.models import CustomUser

class Command(BaseCommand):
    help = 'Checks the status of superuser accounts.'

    def handle(self, *args, **options):
        superusers = CustomUser.objects.filter(is_superuser=True)
        if not superusers.exists():
            self.stdout.write(self.style.WARNING('No superusers found.'))
            return

        self.stdout.write(self.style.SUCCESS('Superuser Account Status:'))
        for user in superusers:
            self.stdout.write(f'  - Username: {user.username}')
            self.stdout.write(f'    is_staff: {user.is_staff}')
            self.stdout.write(f'    role: {user.role}')
            if not user.is_staff:
                self.stdout.write(self.style.ERROR('    ^ This user may not be able to log in to the admin site (/admin/).'))
