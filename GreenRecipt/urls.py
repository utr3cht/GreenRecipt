from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("receipts/", views.ReceiptListView.as_view(), name="receipt_list"),
    path("receipts/new/", views.ReceiptCreateView.as_view(), name="receipt_create"),
    path("inquiries/", views.InquiryListView.as_view(), name="inquiry_list"),
    path("inquiries/new/", views.InquiryCreateView.as_view(), name="inquiry_create"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
