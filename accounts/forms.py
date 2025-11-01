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
