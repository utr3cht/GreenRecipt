# core/models.py
from django.db import models
from django.conf import settings


class Store(models.Model):
    store_name = models.CharField(max_length=64, verbose_name='店舗名')
    category = models.CharField(max_length=64, verbose_name='カテゴリ')
    tel = models.CharField(max_length=32, blank=True, verbose_name='電話番号')
    address = models.CharField(max_length=255, verbose_name='住所')
    open_hours = models.CharField(max_length=20, verbose_name='営業時間')

    def __str__(self):
        return self.store_name

    class Meta:
        verbose_name = '加盟店'
        verbose_name_plural = '加盟店'


class Receipt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, verbose_name='ユーザー')
    store = models.ForeignKey(
        Store, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='店舗')
    scanned_at = models.DateField(auto_now_add=True, verbose_name='スキャン日時')
    ocr_text = models.TextField(blank=True, verbose_name='文字起こし内容')
    image_url = models.URLField(max_length=191, verbose_name='画像URL')

    def __str__(self):
        return f"Receipt {self.id} - {self.scanned_at}"

    class Meta:
        verbose_name = 'レシート'
        verbose_name_plural = 'レシート'


class Inquiry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True, verbose_name='問い合わせユーザー')
    reply_to_email = models.EmailField(
        max_length=100, verbose_name='返信先メールアドレス')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    subject = models.CharField(max_length=100, verbose_name='件名')
    body_text = models.TextField(verbose_name='内容')

    def __str__(self):
        return self.subject

    class Meta:
        verbose_name = 'お問い合わせ'
        verbose_name_plural = 'お問い合わせ'


class Coupon(models.Model):
    title = models.CharField(max_length=64, verbose_name='タイトル')
    description = models.CharField(max_length=64, verbose_name='詳細')
    type = models.CharField(max_length=64, verbose_name='タイプ')
    discount_value = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='割引量')
    available_stores = models.ManyToManyField(
        Store, verbose_name='利用可能店舗', blank=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'クーポン'
        verbose_name_plural = 'クーポン'


class Report(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, verbose_name='ユーザー')
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name='生成日時')
    description = models.TextField(verbose_name='内容')

    def __str__(self):
        return f"Report for {self.user} at {self.generated_at}"

    class Meta:
        verbose_name = 'AIレポート'
        verbose_name_plural = 'AIレポート'
