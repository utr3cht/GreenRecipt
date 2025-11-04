from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path("", views.index, name="index"),
    path("menu/", views.main_menu, name="main_menu"),
    path("coupons/", views.coupon_list, name="coupon_list"),
    path("map/", views.store_map, name="store_map"),
    path("result/", views.result, name="result"),
    path("receipts/", views.scan, name="scan"),
    path("reports/", views.ai_report, name="ai_report"),
    path("inquiries/", views.inquiry, name="inquiry"),
    path('store/help/', views.store_help, name='store_help'),
    path("inquiries/create/", views.inquiry_create, name="inquiry_create"),
    path("inquiries/complete/", views.inquiry_complete, name="inquiry_complete"),
]