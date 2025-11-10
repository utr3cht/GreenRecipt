from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path("", views.index, name="index"),
    path("staff/index",views.staff_index,name="staff_index"),
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