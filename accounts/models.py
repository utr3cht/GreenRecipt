from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


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
    current_points = models.IntegerField(default=0, verbose_name='ポイント')
    rank = models.CharField(max_length=10, default='seed', verbose_name='ランク')
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

    def save(self, *args, **kwargs):
        if not self.is_superuser:
            self.is_staff = self.role in ['admin', 'system', 'store']
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'
