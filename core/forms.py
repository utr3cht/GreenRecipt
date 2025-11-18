from .models import Receipt, Inquiry, Store
from django import forms
from .models import Receipt, Inquiry, Store, Announcement, Coupon
from accounts.models import CustomUser


class ReceiptForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ["image_url"]


class InquiryForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = ["reply_to_email", "subject", "body_text", "image"]


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
        fields = ['title', 'description', 'type', 'discount_value', 'available_stores']
        widgets = {
            'available_stores': forms.CheckboxSelectMultiple,
        }


class GrantCouponForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='user'),
        label="ユーザー"
    )
    coupon = forms.ModelChoiceField(
        queryset=Coupon.objects.all(),
        label="クーポン"
    )


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
        return file

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On create form, there is no instance, so hide the delete checkbox
        if not self.instance or not self.instance.pk:
            del self.fields['delete_file']
