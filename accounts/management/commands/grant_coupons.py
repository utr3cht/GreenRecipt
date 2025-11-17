from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from core.models import Coupon
from django.db.models import Q

class Command(BaseCommand):
    help = 'Grants coupons to users based on their rank.'

    def handle(self, *args, **options):
        # ランクとクーポンのタイトルのマッピング
        rank_coupon_map = {
            'bronze': 'ブロンズランク特典',
            'silver': 'シルバーランク特典',
            'gold': 'ゴールドランク特典',
        }

        # 対象となるクーポンを事前に一括で取得
        try:
            coupons = Coupon.objects.filter(title__in=rank_coupon_map.values())
            coupon_map = {coupon.title: coupon for coupon in coupons}
        except Coupon.DoesNotExist:
            self.stdout.write(self.style.ERROR('Default coupons not found. Please run "create_default_coupons" first.'))
            return

        # 全てのユーザーを取得
        users = CustomUser.objects.filter(role='user')

        granted_count = 0
        for user in users:
            # ユーザーのランクに対応するクーポンのタイトルを取得
            target_coupon_title = rank_coupon_map.get(user.rank.lower())
            
            if not target_coupon_title:
                continue

            # 対応するクーポンオブジェクトを取得
            target_coupon = coupon_map.get(target_coupon_title)
            if not target_coupon:
                self.stdout.write(self.style.WARNING(f'Coupon "{target_coupon_title}" not found in database.'))
                continue

            # ユーザーが既にそのクーポンを持っているか確認
            if not user.current_coupons.filter(pk=target_coupon.pk).exists():
                # クーポンを付与
                user.current_coupons.add(target_coupon)
                granted_count += 1
                self.stdout.write(f'Granted "{target_coupon.title}" to user {user.username}.')

        self.stdout.write(self.style.SUCCESS(f'Successfully granted coupons to {granted_count} users.'))
