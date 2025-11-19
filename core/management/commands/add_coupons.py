from django.core.management.base import BaseCommand
from core.models import Coupon
from decimal import Decimal

class Command(BaseCommand):
    help = 'Creates a set of default coupons in the database.'

    def handle(self, *args, **options):
        coupons_to_create = [
            {
                "title": "お会計から10%割引",
                "description": "すべてのお会計が10%オフになります。",
                "type": "percentage",
                "discount_value": Decimal("10.00"),
            },
            {
                "title": "500円引きクーポン",
                "description": "3000円以上のお会計で500円引き。",
                "type": "absolute",
                "discount_value": Decimal("500.00"),
            },
            {
                "title": "ドリンク1杯無料",
                "description": "お好きなドリンクを1杯無料でご提供。",
                "type": "absolute", # This could be modeled differently, but for simplicity...
                "discount_value": Decimal("0.00"), # Or the price of a standard drink
            },
            {
                "title": "初回限定！20%オフ",
                "description": "初めてご利用のお客様限定で20%オフ！",
                "type": "percentage",
                "discount_value": Decimal("20.00"),
            },
        ]

        self.stdout.write("Creating default coupons...")
        count = 0
        for coupon_data in coupons_to_create:
            coupon, created = Coupon.objects.get_or_create(
                title=coupon_data["title"],
                defaults=coupon_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created coupon: "{coupon.title}"'))
                count += 1
            else:
                self.stdout.write(self.style.WARNING(f'Coupon "{coupon.title}" already exists.'))

        self.stdout.write(self.style.SUCCESS(f'Finished creating coupons. {count} new coupons were added.'))
