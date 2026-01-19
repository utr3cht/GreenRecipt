from django.core.management.base import BaseCommand
from core.utils import fetch_emails_from_gmail

class Command(BaseCommand):
    help = 'Fetch emails from Gmail and import them as InquiryMessages'

    def handle(self, *args, **options):
        success, message = fetch_emails_from_gmail()
        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.ERROR(message))
