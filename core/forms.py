from .models import Receipt, Inquiry, Store
from django import forms
from .models import Receipt, Inquiry, Store, Announcement, Coupon, EcoProduct
from accounts.models import CustomUser


class ReceiptForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ["image_url"]


class InquiryForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = ["reply_to_email", "subject", "body_text", "image"]

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # 拡張子の確認
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            ext = '.' + image.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise ValidationError("許可されていないファイル形式です。画像ファイル（jpg, jpeg, png, webp）をアップロードしてください。")
            
            # ファイルサイズの確認 (5MB制限)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("ファイルサイズは5MB以下にしてください。")
        return image


class ReplyForm(forms.Form):
    subject = forms.CharField(label='件名', max_length=100)
    message = forms.CharField(label='メッセージ', widget=forms.Textarea)


class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['store_name', 'category', 'tel',
                  'address', 'open_time', 'close_time']


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['title', 'description', 'requirement', 'required_points', 'type', 'discount_value', 'available_stores']
        widgets = {
            'available_stores': forms.CheckboxSelectMultiple,
        }


from django.db.models import Q

class GrantCouponForm(forms.Form):
    target_all = forms.BooleanField(
        required=False, 
        label="全ユーザー（条件合致者）に配布",
        help_text="チェックを入れると、必要ポイント数を満たしている全てのユーザーに配布します。"
    )
    user = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='user'),
        label="ユーザー",
        required=False
    )
    coupon = forms.ModelChoiceField(
        queryset=Coupon.objects.all(),
        label="クーポン"
    )

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)
        
        # 店舗スタッフの場合は自店のクーポンまたは運営共通クーポン（store=None）を表示
        if self.request_user and self.request_user.role == 'store' and self.request_user.store:
            self.fields['coupon'].queryset = Coupon.objects.filter(
                Q(store=self.request_user.store) | Q(store__isnull=True)
            )
        
        # 承認済みクーポンのみ表示
        current_qs = self.fields['coupon'].queryset
        self.fields['coupon'].queryset = current_qs.filter(status='approved')

    def clean(self):
        cleaned_data = super().clean()
        target_all = cleaned_data.get('target_all')
        user = cleaned_data.get('user')

        if not target_all and not user:
            raise forms.ValidationError("ユーザーを選択するか、「全ユーザーに配布」にチェックを入れてください。")
        return cleaned_data


from django.core.exceptions import ValidationError

class AnnouncementForm(forms.ModelForm):
    delete_file = forms.BooleanField(required=False, label="既存のファイルを削除する")

    class Meta:
        model = Announcement
        fields = ['title', 'content', 'file', 'delete_file']
        widgets = {
            'file': forms.FileInput,
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            allowed_extensions = ['.jpg', '.jpeg', '.png', 'gif', '.webp', '.mp4', 'mov', '.avi', '.wmv']
            ext = '.' + file.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise ValidationError("許可されていないファイル形式です。画像または動画ファイルをアップロードしてください。")
            
            # ファイルサイズの確認 (10MB制限)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("ファイルサイズは10MB以下にしてください。")
        return file

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 作成時は削除フィールドを隠す
        if not self.instance or not self.instance.pk:
            del self.fields['delete_file']


class EcoProductForm(forms.ModelForm):
    class Meta:
        model = EcoProduct
        fields = ['name', 'jan_code', 'points', 'is_common']
        widgets = {
            'jan_code': forms.TextInput(attrs={'pattern': r'\d*', 'inputmode': 'numeric'}),
        }


class StoreEcoProductForm(forms.ModelForm):
    class Meta:
        model = EcoProduct
        fields = ['name', 'jan_code', 'points', 'remarks']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'jan_code': forms.TextInput(attrs={'class': 'form-control', 'pattern': r'\d*', 'inputmode': 'numeric'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '承認者への申し送り事項など'}),
        }

class StoreCouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['title', 'type', 'discount_value', 'requirement', 'required_points', 'description', 'remarks']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'requirement': forms.TextInput(attrs={'class': 'form-control'}),
            'required_points': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
