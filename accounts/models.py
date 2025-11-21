from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from core.models import Coupon


class CustomUser(AbstractUser):
    username = models.CharField(
        "ユーザー名",
        max_length=50,
        unique=True,
        help_text=(
            "必須。50文字以下。文字、数字、および @/./+/-/_ のみ使用できます。"
        ),
        validators=[AbstractUser.username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    email = models.EmailField(_("email address"), unique=True)
    is_verified = models.BooleanField(default=False, verbose_name='メール認証済み')
    verification_token = models.CharField(
        max_length=100, blank=True, null=True, unique=True, verbose_name='認証トークン')
    ROLE_CHOICES = (
        ('admin', '管理者'),
        ('store', '店舗'),
        ('user', '一般ユーザー'),
    )
    RANK_CHOICES = (
        ('seed', '種'),
        ('sprout', '芽'),
        ('tree', '木'),
        ('apple_tree', 'リンゴの木'),
    )
    current_points = models.IntegerField(default=0, verbose_name='ポイント')
    rank = models.CharField(max_length=20, choices=RANK_CHOICES, default='seed', verbose_name='ランク')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='アカウント更新日時')
    birthday = models.DateField(verbose_name='生年月日', null=True, blank=True)
    purchased_amount = models.IntegerField(default=0, verbose_name='購入点数')
    lastmonth_point = models.IntegerField(default=0, verbose_name='先月獲得ポイント')
    current_coupons = models.ManyToManyField(
        'core.Coupon', verbose_name='所持クーポン', blank=True)
    role = models.CharField(
        max_length=10, choices=ROLE_CHOICES, default='user', verbose_name='役割')
    store = models.ForeignKey(
        'core.Store', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='所属店舗')

    new_email = models.EmailField(
        _("new email address"), blank=True, null=True)
    email_change_token = models.CharField(
        max_length=100, blank=True, null=True, unique=True, verbose_name='メール変更認証トークン'
    )

    # ランク階層を定義
    RANK_HIERARCHY = {'seed': 0, 'sprout': 1, 'tree': 2, 'apple_tree': 3}

    def _update_rank(self):
        """ポイントに基づいてランクを更新する"""
        points = self.current_points
        new_rank = self.rank

        if points >= 800:
            new_rank = 'apple_tree'
        elif points >= 300:
            new_rank = 'tree'
        elif points >= 100:
            new_rank = 'sprout'
        else:
            new_rank = 'seed'
        
        self.rank = new_rank

    def add_points(self, points):
        """ポイントを加算し、ランクを更新して保存する"""
        self.current_points += points
        self._update_rank()
        self.save()

    def save(self, *args, **kwargs):
        # --- 1. ランクとポイントの更新前処理 ---
        is_new_user = self.pk is None
        old_rank = 'seed'
        old_points = 0
        if not is_new_user:
            try:
                # データベースから保存前の状態を取得
                old_self = CustomUser.objects.get(pk=self.pk)
                old_rank = old_self.rank
                old_points = old_self.current_points
            except CustomUser.DoesNotExist:
                # 予期せぬエラーケース（ユーザーが存在しない）
                pass

        # --- 2. ランクの自動更新 ---
        self._update_rank()
        
        # --- 3. Djangoのデフォルトのsave処理を呼び出す ---
        if not self.is_superuser:
            self.is_staff = self.role in ['admin', 'system', 'store']
        super().save(*args, **kwargs)

        # --- 4. クーポン付与ロジック（save後に行う） ---
        # ランクアップ時のクーポン付与
        rank_coupon_map = {
            'sprout': 'ブロンズランク特典', # クーポン名は既存のままか確認が必要だが、一旦コード上のキーを変更
            'tree': 'シルバーランク特典',
            'apple_tree': 'ゴールドランク特典',
        }
        if self.RANK_HIERARCHY.get(self.rank, -1) > self.RANK_HIERARCHY.get(old_rank, -1):
            coupon_title = rank_coupon_map.get(self.rank)
            if coupon_title:
                try:
                    coupon_to_grant = Coupon.objects.get(title=coupon_title)
                    # 既に持っていない場合のみ付与
                    if not self.current_coupons.filter(pk=coupon_to_grant.pk).exists():
                        self.current_coupons.add(coupon_to_grant)
                except Coupon.DoesNotExist:
                    # 対応するクーポンが存在しない場合は何もしない
                    pass

        # 特定ポイント達成時のクーポン付与
        if old_points < 1000 <= self.current_points:
            try:
                coupon_to_grant = Coupon.objects.get(title='1000ポイント達成記念')
                if not self.current_coupons.filter(pk=coupon_to_grant.pk).exists():
                    self.current_coupons.add(coupon_to_grant)
            except Coupon.DoesNotExist:
                pass

    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'
