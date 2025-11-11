
import os
from django.core.management.base import BaseCommand, CommandError
from core.models import Inquiry

class Command(BaseCommand):
    help = 'Checks a specific inquiry with an image and prints its details.'

    def add_arguments(self, parser):
        parser.add_argument('inquiry_id', type=int, help='The ID of the inquiry to check.')

    def handle(self, *args, **options):
        inquiry_id = options['inquiry_id']
        try:
            inquiry = Inquiry.objects.get(pk=inquiry_id)
        except Inquiry.DoesNotExist:
            raise CommandError(f'Inquiry with ID "{inquiry_id}" does not exist.')

        self.stdout.write(f"Checking details for Inquiry ID: {inquiry.id}")
        self.stdout.write("-" * 30)

        if inquiry.image:
            self.stdout.write(self.style.SUCCESS(f"Image field has a value: {inquiry.image}"))
            
            # 1. Print Django's perspective
            try:
                image_url = inquiry.image.url
                self.stdout.write(f"  - Django's generated URL (.url): {image_url}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Could not get .url property: {e}"))

            try:
                image_path = inquiry.image.path
                self.stdout.write(f"  - Django's expected path (.path): {image_path}")

                # 2. Check if the file actually exists
                if os.path.exists(image_path):
                    self.stdout.write(self.style.SUCCESS("  - File EXISTS at the expected path."))
                else:
                    self.stdout.write(self.style.ERROR("  - File DOES NOT EXIST at the expected path."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Could not get .path property or check existence: {e}"))

        else:
            self.stdout.write(self.style.WARNING("This inquiry does not have an image associated with it."))
        
        self.stdout.write("-" * 30)
