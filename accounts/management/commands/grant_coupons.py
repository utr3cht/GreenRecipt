from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from core.models import Coupon
from django.db.models import Q

class Command(BaseCommand):
    help = 'ランクに基づいてユーザーにクーポンを付与します。'

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
            self.stdout.write(self.style.ERROR('デフォルトクーポンが見つかりません。"create_default_coupons" を先に実行してください。'))
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
                self.stdout.write(self.style.WARNING(f'クーポン "{target_coupon_title}" がデータベースに見つかりません。'))
                continue

            # ユーザーが既にそのクーポンを持っているか確認
            if not user.current_coupons.filter(pk=target_coupon.pk).exists():
                # クーポンを付与
                user.current_coupons.add(target_coupon)
                granted_count += 1
                self.stdout.write(f'ユーザー {user.username} に "{target_coupon.title}" を付与しました。')

        self.stdout.write(self.style.SUCCESS(f'{granted_count} 人のユーザーにクーポン付与が完了しました。'))
