from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView
from django.core.mail import send_mail
from .models import Receipt, Inquiry
from .forms import ReceiptForm, InquiryForm


class ReceiptListView(ListView):
    model = Receipt
    template_name = "core/receipt_list.html"
    ordering = ["-created_at"]


class ReceiptCreateView(CreateView):
    model = Receipt
    form_class = ReceiptForm
    template_name = "core/receipt_create.html"
    success_url = reverse_lazy("receipt_list")


class InquiryListView(ListView):
    model = Inquiry
    template_name = "core/inquiry_list.html"
    ordering = ["-created_at"]


class InquiryCreateView(CreateView):
    model = Inquiry
    form_class = InquiryForm
    template_name = "core/inquiry_create.html"
    success_url = reverse_lazy("inquiry_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        send_mail(
            "お問い合わせ受付",
            "お問い合わせを受け付けました。",
            "noreply@example.com",
            [form.instance.email],
        )
        return response
