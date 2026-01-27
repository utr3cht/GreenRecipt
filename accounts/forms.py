from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser
import datetime


class CustomUserCreationForm(UserCreationForm):
    birthday = forms.DateField(
        label='生年月日',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'min': '1920-01-01',
            'max': datetime.date.today().isoformat()
        })
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'birthday',)


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'birthday',)


class CustomAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        # 役割チェック
        if user.role != 'user':
            raise forms.ValidationError(
                "ユーザー名もしくはパスワードが正しくありません。", # エラーメッセージ
                code='invalid_role'
            )

        # メール認証チェック
        if not user.is_verified:
            raise forms.ValidationError(
                "メールアドレスが認証されていません。メールをご確認ください。",
                code='unverified_email'
            )

class StoreUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email',)

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("このユーザー名は既に使用されています。")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("このメールアドレスは既に使用されています。")
        return email
