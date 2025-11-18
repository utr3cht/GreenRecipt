from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path("", views.index, name="index"),
    path("staff/index",views.staff_index,name="staff_index"),
    path("menu/", views.main_menu, name="main_menu"),
    path("coupons/", views.coupon_list, name="coupon_list"),
    path("map/", views.store_map, name="store_map"),
    path('history/', views.receipt_history, name='receipt_history'),
    path('receipt/<int:receipt_id>/', views.receipt_detail, name='receipt_detail'),
    path("receipts/", views.scan, name="scan"),
    path("reports/", views.ai_report, name="ai_report"),
    path("inquiries/", views.inquiry, name="inquiry"),
    path('store/help/', views.store_help, name='store_help'),
    path("staff/inquiry/", views.staff_inquiry, name="staff_inquiry"),

    path("staff/inquiry/complete/", views.staff_inquiry_complete, name="staff_inquiry_complete"),
    path("staff/announcements/", views.announcement_list, name="announcement_list"),
    path("staff/announcement/create/", views.announcement_create, name="announcement_create"),
    path("staff/announcement/<int:announcement_id>/update/", views.announcement_update, name="announcement_update"),
    path("staff/announcement/<int:announcement_id>/delete/", views.announcement_delete, name="announcement_delete"),
    path("staff/announcement/<int:announcement_id>/", views.announcement_detail, name="announcement_detail"),

    path("staff/coupons/", views.coupon_list_admin, name="coupon_list_admin"),
    path("staff/coupons/create/", views.coupon_create, name="coupon_create"),
    path("staff/coupons/<int:coupon_id>/update/", views.coupon_update, name="coupon_update"),
    path("staff/coupons/<int:coupon_id>/delete/", views.coupon_delete, name="coupon_delete"),
    path("staff/coupons/grant/", views.grant_coupon_admin, name="grant_coupon_admin"),

    path("inquiries/complete/", views.inquiry_complete, name="inquiry_complete"),
    path("staff/login/",views.admin_login,name="staff_login"),
    path("staff/logout/", views.staff_logout, name="staff_logout"),
    path("staff/inquiries/dashboard/", views.admin_inquiry_dashboard, name="admin_inquiry_dashboard"),
    path("staff/inquiries/<int:inquiry_id>/", views.inquiry_detail, name="inquiry_detail"),
    path("store/list/",views.store_list,name='store_list'),
    path("staff/stores/<int:store_id>/", views.store_detail, name="store_detail"),
    path("staff/stores/create/", views.store_create, name="store_create"),
    path("staff/stores/<int:store_id>/edit/", views.store_edit, name="store_edit"),
    path("staff/stores/<int:store_id>/add_user/", views.store_add_user, name="store_add_user"),
    path("staff/users/<int:user_id>/delete/", views.store_delete_user, name="store_delete_user"),

]