from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Count

class Command(BaseCommand):
    help = 'Finds and reports duplicate email addresses in the CustomUser model.'

    def handle(self, *args, **options):
        User = get_user_model()

        # Find duplicate emails
        duplicates = User.objects.values('email') \
            .annotate(email_count=Count('email')) \
            .filter(email_count__gt=1, email__isnull=False)

        if duplicates.exists():
            self.stdout.write(self.style.WARNING('Found duplicate email addresses:'))
            for item in duplicates:
                email = item['email']
                count = item['email_count']
                self.stdout.write(f'- Email: {email}, Count: {count}')
                users_with_duplicate_email = User.objects.filter(email=email)
                for user in users_with_duplicate_email:
                    self.stdout.write(f'  - User ID: {user.id}, Username: {user.username}')
        else:
            self.stdout.write(self.style.SUCCESS('No duplicate email addresses found.'))

        # Check for users with null emails (if email field is not null=True)
        null_emails = User.objects.filter(email__isnull=True)
        if null_emails.exists():
            self.stdout.write(self.style.WARNING('Found users with NULL email addresses:'))
            for user in null_emails:
                self.stdout.write(f'- User ID: {user.id}, Username: {user.username}')
        else:
            self.stdout.write(self.style.SUCCESS('No users with NULL email addresses found.'))
