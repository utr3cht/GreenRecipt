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

        # 最初に役割をチェック
        if user.role != 'user':
            raise forms.ValidationError(
                "ユーザー名もしくはパスワードが正しくありません。", # ご指定のメッセージに変更
                code='invalid_role'
            )

        # 役割が'user'の場合のみ、メール認証をチェック
        if not user.is_verified:
            raise forms.ValidationError(
                "メールアドレスが認証されていません。メールをご確認ください。",
                code='unverified_email'
            )
