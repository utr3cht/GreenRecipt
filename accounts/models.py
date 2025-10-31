from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('system', 'システム管理者'),
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

    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'
