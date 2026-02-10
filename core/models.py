# core/models.py
from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
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
            # Nominatimでジオコーディングを試行
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
            time.sleep(1) # Nominatimサービスへの負荷軽減

            # Nominatim失敗時はGoogle Mapsを使用
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
    transaction_time = models.DateTimeField(null=True, blank=True, verbose_name='取引日時')
    ocr_text = models.TextField(blank=True, verbose_name='文字起こし内容')
    image_url = models.URLField(max_length=191, verbose_name='画像URL')
    parsed_data = models.JSONField(null=True, blank=True, verbose_name='解析済みデータ')
    points_earned = models.IntegerField(default=0, verbose_name='獲得ポイント')

    def __str__(self):
        return f"Receipt {self.id} - {self.scanned_at}"

    @property
    def total_quantity(self):
        """
        parsed_dataから合計購入点数を計算して返す。
        直接抽出された合計点数を優先する。
        """
        if isinstance(self.parsed_data, dict):
            # 直接抽出された合計点数があればそれを返す
            if 'total_quantity' in self.parsed_data and self.parsed_data['total_quantity'] > 0:
                return self.parsed_data['total_quantity']
            if 'items' in self.parsed_data and isinstance(self.parsed_data['items'], list):
                return sum(item.get('quantity', 0) for item in self.parsed_data['items'])
        if isinstance(self.parsed_data, list):
            return sum(item.get('quantity', 0) for item in self.parsed_data)
        return 0

    @property
    def total_amount(self):
        """
        parsed_dataから合計金額を計算して返す。
        """
        if isinstance(self.parsed_data, dict):
            return self.parsed_data.get('total_amount', 0)
        return 0

    @property
    def ec_points(self):
        """
        獲得ポイントを返す。
        後方互換性のためにプロパティ名を維持するが、実態はpoints_earnedを返す。
        """
        return self.points_earned

    class Meta:
        verbose_name = 'レシート'
        verbose_name_plural = 'レシート'


class Product(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name='商品名')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品'


class ReceiptItem(models.Model):
    receipt = models.ForeignKey(
        Receipt, related_name='items', on_delete=models.CASCADE, verbose_name='レシート')
    # 商品マスターは消さない
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, verbose_name='商品')
    quantity = models.IntegerField(verbose_name='数量')
    price = models.IntegerField(verbose_name='価格')
    points = models.IntegerField(default=0, verbose_name='獲得ポイント')

    def __str__(self):
        return f"{self.product.name} ({self.quantity} x ¥{self.price})"

    class Meta:
        verbose_name = 'レシート項目'
        verbose_name_plural = 'レシート項目'


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
    STATUS_CHOICES = (
        ('unanswered', '未対応'),
        ('in_progress', '対応中'),
        ('completed', '完了'),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='unanswered', verbose_name='ステータス')
    is_replied = models.BooleanField(default=False, verbose_name='返信済み')
    reply_message = models.TextField(blank=True, verbose_name='返信内容')

    def __str__(self):
        return self.subject

    @property
    def last_message_is_user(self):
        last_msg = self.messages.order_by('-created_at').first()
        return last_msg and last_msg.sender_type == 'user'

    class Meta:
        verbose_name = 'お問い合わせ'
        verbose_name_plural = 'お問い合わせ'


class InquiryMessage(models.Model):
    inquiry = models.ForeignKey(Inquiry, related_name='messages', on_delete=models.CASCADE, verbose_name='お問い合わせ')
    sender_type = models.CharField(max_length=10, choices=[('admin', '管理者'), ('user', 'ユーザー')], verbose_name='送信者タイプ')
    message = models.TextField(verbose_name='メッセージ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    def __str__(self):
        return f"{self.sender_type}: {self.message[:20]}"

    class Meta:
        verbose_name = 'お問い合わせメッセージ'
        verbose_name_plural = 'お問い合わせメッセージ'



class Coupon(models.Model):
    TYPE_CHOICES = [
        ('percentage', '割引率'),
        ('absolute', '固定額'),
    ]
    title = models.CharField(max_length=64, verbose_name='タイトル')
    description = models.CharField(max_length=64, verbose_name='詳細')
    requirement = models.CharField(max_length=255, blank=True, verbose_name='利用条件')
    type = models.CharField(max_length=64, verbose_name='タイプ', choices=TYPE_CHOICES)
    discount_value = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='割引量',validators=[MinValueValidator(1)])
    available_stores = models.ManyToManyField(
        Store, verbose_name='利用可能店舗', blank=True)
    required_points = models.IntegerField(default=0, verbose_name='必要ポイント数', validators=[MinValueValidator(0)])
    
    # 承認フロー用
    STATUS_CHOICES = [
        ('pending', '申請中'),
        ('approved', '承認済み'),
        ('rejected', '却下'),
        ('deletion_requested', '削除申請中'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='approved', verbose_name='ステータス')
    store = models.ForeignKey(
        Store, on_delete=models.CASCADE, null=True, blank=True, related_name='created_coupons', verbose_name='作成店舗')
    remarks = models.TextField(blank=True, verbose_name='備考')
    rejection_reason = models.TextField(blank=True, verbose_name='却下理由')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    @property
    def discount_amount(self):
        if self.type == 'absolute':
            return int(self.discount_value)
        return None

    @property
    def discount_rate(self):
        if self.type == 'percentage':
            return int(self.discount_value)
        return None

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'クーポン'
        verbose_name_plural = 'クーポン'


class CouponUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='ユーザー')
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, verbose_name='クーポン')
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='利用店舗')
    used_at = models.DateTimeField(auto_now_add=True, verbose_name='利用日時')

    def __str__(self):
        return f"{self.user} used {self.coupon} at {self.store}"

    class Meta:
        verbose_name = 'クーポン利用履歴'
        verbose_name_plural = 'クーポン利用履歴'


class Report(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, verbose_name='ユーザー')
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name='生成日時')
    description = models.TextField(verbose_name='内容')
    score = models.IntegerField(default=0, verbose_name='スコア')
    
    # レポート時点のスナップショット
    rank = models.CharField(max_length=20, blank=True, null=True, verbose_name='会員ランク')
    monthly_points = models.IntegerField(default=0, verbose_name='月間獲得ポイント')
    held_points = models.IntegerField(default=0, verbose_name='その月の所持ポイント')

    def __str__(self):
        return f"Report for {self.user} at {self.generated_at}"

    class Meta:
        verbose_name = 'AIレポート'
        verbose_name_plural = 'AIレポート'


from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

class Announcement(models.Model):
    title = models.CharField(max_length=100, verbose_name='記事名')
    content = models.TextField(verbose_name='内容')
    file = models.FileField(
        upload_to='announcements/', null=True, blank=True, verbose_name='ファイル')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    def __str__(self):
        return self.title

    @property
    def is_image(self):
        if self.file:
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            return any(self.file.name.lower().endswith(ext) for ext in image_extensions)
        return False

    @property
    def is_video(self):
        if self.file:
            video_extensions = ['.mp4', '.mov', '.avi', '.wmv']
            return any(self.file.name.lower().endswith(ext) for ext in video_extensions)
        return False

    def save(self, *args, **kwargs):
        if self.file and self.is_image and self._state.adding:
            pil_image = Image.open(self.file)

            if pil_image.width > 1200:
                new_width = 1200
                new_height = int((new_width / pil_image.width) * pil_image.height)
                resized_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                buffer = BytesIO()
                img_format = pil_image.format or 'JPEG'
                resized_image.save(buffer, format=img_format)
                
                file_name = self.file.name
                self.file = ContentFile(buffer.getvalue(), name=file_name)

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'お知らせ'
        verbose_name_plural = 'お知らせ'


class EcoProduct(models.Model):
    name = models.CharField(
        max_length=255, unique=True, verbose_name='エコ商品名/キーワード')
    jan_code = models.CharField(
        max_length=13, blank=True, null=True, unique=True, verbose_name='JANコード',
        validators=[RegexValidator(r'^\d+$', 'JANコードは数字のみ入力してください。')]
        )
    points = models.IntegerField(default=10, verbose_name='付与ポイント', validators=[MinValueValidator(1)])
    
    # 申請用フィールド
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, verbose_name='店舗')
    remarks = models.TextField(blank=True, verbose_name='備考')
    is_common = models.BooleanField(default=False, verbose_name='共通商品')
    
    STATUS_CHOICES = [
        ('pending', '申請中'),
        ('approved', '承認済み'),
        ('rejected', '却下'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='approved', verbose_name='ステータス')
    rejection_reason = models.TextField(blank=True, verbose_name='却下理由')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    def __str__(self):
        return f"{self.name} ({self.points} pts)"

    class Meta:
        verbose_name = 'エコ商品'
        verbose_name_plural = 'エコ商品'
