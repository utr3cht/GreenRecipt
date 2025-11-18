from django.core.management.base import BaseCommand
from core.models import Coupon

class Command(BaseCommand):
    help = 'Creates default coupons for different ranks'

    def handle(self, *args, **options):
        coupons_to_create = [
            {
                'title': 'ブロンズランク特典',
                'description': '全商品10%割引',
                'type': 'percentage',
                'discount_value': 10.00,
            },
            {
                'title': 'シルバーランク特典',
                'description': '全商品20%割引',
                'type': 'percentage',
                'discount_value': 20.00,
            },
            {
                'title': 'ゴールドランク特典',
                'description': '500円割引',
                'type': 'absolute',
                'discount_value': 500.00,
            },
        ]

        for coupon_data in coupons_to_create:
            coupon, created = Coupon.objects.get_or_create(
                title=coupon_data['title'],
                defaults=coupon_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created coupon: "{coupon.title}"'))
            else:
                self.stdout.write(self.style.WARNING(f'Coupon "{coupon.title}" already exists.'))
