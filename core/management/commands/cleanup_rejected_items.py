from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import EcoProduct, Coupon
from datetime import timedelta

class Command(BaseCommand):
    help = 'Deletes rejected EcoProducts and Coupons that haven\'t been updated for 7 days.'

    def handle(self, *args, **options):
        threshold_date = timezone.now() - timedelta(days=7)
        
        # Cleanup EcoProducts
        rejected_products = EcoProduct.objects.filter(status='rejected', updated_at__lt=threshold_date)
        product_count = rejected_products.count()
        rejected_products.delete()
        
        # Cleanup Coupons
        rejected_coupons = Coupon.objects.filter(status='rejected', updated_at__lt=threshold_date)
        coupon_count = rejected_coupons.count()
        rejected_coupons.delete()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {product_count} rejected products and {coupon_count} rejected coupons older than {threshold_date}.'))
