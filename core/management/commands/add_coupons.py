from django.core.management.base import BaseCommand
from core.models import Coupon
from decimal import Decimal

class Command(BaseCommand):
    help = 'データベースにデフォルトのクーポンを作成します。'

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
                "type": "absolute", # 別のモデル化も可能だが簡略化のため
                "discount_value": Decimal("0.00"), # 標準的なドリンク価格でも可
            },
            {
                "title": "初回限定！20%オフ",
                "description": "初めてご利用のお客様限定で20%オフ！",
                "type": "percentage",
                "discount_value": Decimal("20.00"),
            },
        ]

        self.stdout.write("デフォルトクーポンを作成中...")
        count = 0
        for coupon_data in coupons_to_create:
            coupon, created = Coupon.objects.get_or_create(
                title=coupon_data["title"],
                defaults=coupon_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'クーポンを作成しました: "{coupon.title}"'))
                count += 1
            else:
                self.stdout.write(self.style.WARNING(f'クーポンは既に存在します: "{coupon.title}"'))

        self.stdout.write(self.style.SUCCESS(f'クーポンの作成が完了しました。{count} 件追加されました。'))
