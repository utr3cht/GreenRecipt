from django import forms
from .models import Receipt, Inquiry


class ReceiptForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ["image"]


class InquiryForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = ["email", "subject", "body"]
