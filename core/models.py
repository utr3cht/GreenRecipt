# core/models.py
from django.db import models
from django.conf import settings
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import googlemaps


class Store(models.Model):
    store_id = models.AutoField(primary_key=True, verbose_name='店舗ID')
    store_name = models.CharField(max_length=64, verbose_name='店舗名')
    CATEGORY_CHOICES = [
        ('restaurant', '飲食店'),
        ('retail', '小売店'),
        ('service', 'サービス業'),
        ('other', 'その他'),
    ]
    category = models.CharField(max_length=64, choices=CATEGORY_CHOICES, verbose_name='カテゴリ')
    tel = models.CharField(max_length=32, blank=True, verbose_name='電話番号')
    address = models.CharField(max_length=255, verbose_name='住所')
    open_time = models.TimeField(verbose_name='開店時間', null=True, blank=True)
    close_time = models.TimeField(verbose_name='閉店時間', null=True, blank=True)
    lat = models.FloatField(verbose_name='緯度', default=0.0)
    lng = models.FloatField(verbose_name='経度', default=0.0)

    def __str__(self):
        return self.store_name

    def save(self, *args, **kwargs):
        if self.address and self.lat == 0.0 and self.lng == 0.0:
            geolocated = False
            # Try Nominatim first
            geolocator = Nominatim(user_agent="GreenRecipt_Geocoder")
            try:
                encoded_address = self.address.encode('utf-8').decode('utf-8')
                location = geolocator.geocode(encoded_address, timeout=10, language='ja')
                if location:
                    self.lat = location.latitude
                    self.lng = location.longitude
                    geolocated = True
                    print(f"Nominatim geocoded store {self.store_name}: {self.address} -> ({self.lat}, {self.lng})")
                else:
                    print(f"Nominatim could not geocode address for store {self.store_name}: {self.address}")
            except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
                print(f"Nominatim geocoding failed for store {self.store_name}: {self.address} - {e}")
            time.sleep(1) # Be kind to the Nominatim service

            # If Nominatim failed and Google Maps geocoding is enabled, try Google Maps
            if not geolocated and settings.GOOGLE_MAPS_GEOCODING_ENABLED and settings.GOOGLE_MAPS_API_KEY and settings.GOOGLE_MAPS_API_KEY != 'YOUR_GOOGLE_MAPS_API_KEY':
                try:
                    gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
                    geocode_result = gmaps.geocode(self.address, language='ja')
                    if geocode_result:
                        self.lat = geocode_result[0]['geometry']['location']['lat']
                        self.lng = geocode_result[0]['geometry']['location']['lng']
                        geolocated = True
                        print(f"Google Maps geocoded store {self.store_name}: {self.address} -> ({self.lat}, {self.lng})")
                    else:
                        print(f"Google Maps could not geocode address for store {self.store_name}: {self.address}")
                except Exception as e:
                    print(f"Google Maps geocoding failed for store {self.store_name}: {self.address} - {e}")

        super().save(*args, **kwargs)

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
    image = models.ImageField(
        upload_to='inquiries/', null=True, blank=True, verbose_name='添付画像')
    is_replied = models.BooleanField(default=False, verbose_name='返信済み')
    reply_message = models.TextField(blank=True, verbose_name='返信内容')

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
