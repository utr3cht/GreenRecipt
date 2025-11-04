from django import forms
from .models import Receipt, Inquiry


class ReceiptForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ["image_url"]


class InquiryForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = ["reply_to_email", "subject", "body_text", "image"]
