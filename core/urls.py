from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # --- 一般ユーザー向け ---
    path("", views.index, name="index"),
    path("menu/", views.main_menu, name="main_menu"),
    path("coupons/", views.coupon_list, name="coupon_list"),
    path('coupons/acquire/<int:coupon_id>/', views.acquire_coupon, name='acquire_coupon'),
    path('coupons/use/<int:coupon_id>/', views.use_coupon, name='use_coupon'),
    path("map/", views.store_map, name="store_map"),
    path('history/', views.receipt_history, name='receipt_history'),
    path('receipt/<int:receipt_id>/', views.receipt_detail, name='receipt_detail'),
    path("receipts/", views.scan, name="scan"),
    path("reports/", views.ai_report, name="ai_report"),
    path("inquiries/", views.inquiry, name="inquiry"),
    path("inquiries/complete/", views.inquiry_complete, name="inquiry_complete"),

    # --- 管理者・店舗スタッフ共通 ---
    path("staff/index/", views.staff_index, name="staff_index"),
    path("staff/login/", views.admin_login, name="staff_login"),
    path("staff/logout/", views.staff_logout, name="staff_logout"),
    path("staff/help/", views.store_help, name="store_help"),
    path("staff/inquiry/", views.staff_inquiry, name="staff_inquiry"),
    path("staff/inquiry/complete/", views.staff_inquiry_complete, name="staff_inquiry_complete"),

    # --- お知らせ管理 ---
    path("staff/announcements/", views.announcement_list, name="announcement_list"),
    path("staff/announcement/create/", views.announcement_create, name="announcement_create"),
    path("staff/announcement/<int:announcement_id>/update/", views.announcement_update, name="announcement_update"),
    path("staff/announcement/<int:announcement_id>/delete/", views.announcement_delete, name="announcement_delete"),
    path("staff/announcement/<int:announcement_id>/", views.announcement_detail, name="announcement_detail"),

    # --- クーポン管理 ---
    path("staff/coupons/", views.coupon_list_admin, name="coupon_list_admin"),
    path("staff/coupons/create/", views.coupon_create, name="coupon_create"),
    path("staff/coupons/<int:coupon_id>/update/", views.coupon_update, name="coupon_update"),
    path("staff/coupons/<int:coupon_id>/delete/", views.coupon_delete, name="coupon_delete"),
    path("staff/coupons/grant/", views.grant_coupon_admin, name="grant_coupon_admin"),
    path("staff/coupons/<int:coupon_id>/stats/", views.coupon_stats_detail, name="coupon_stats_detail"),

    # --- お問い合わせ管理 ---
    path("staff/inquiries/dashboard/", views.admin_inquiry_dashboard, name="admin_inquiry_dashboard"),
    path("staff/inquiries/<int:inquiry_id>/", views.inquiry_detail, name="inquiry_detail"),

    # --- 店舗管理 ---
    path("staff/stores/", views.store_list, name='store_list'),
    path("staff/stores/create/", views.store_create, name="store_create"),
    path("staff/stores/<int:store_id>/", views.store_detail, name="store_detail"),
    path("staff/stores/<int:store_id>/edit/", views.store_edit, name="store_edit"),
    path("staff/stores/<int:store_id>/add_user/", views.store_add_user, name="store_add_user"),
    path("staff/users/<int:user_id>/delete/", views.store_delete_user, name="store_delete_user"),

    # --- EcoProduct管理 ---
    path("staff/ecoproducts/", views.EcoProductListView.as_view(), name="ecoproduct_list"),
    path("staff/ecoproducts/create/", views.EcoProductCreateView.as_view(), name="ecoproduct_create"),
    path("staff/ecoproducts/<int:pk>/edit/", views.EcoProductUpdateView.as_view(), name="ecoproduct_update"),
    path("staff/ecoproducts/<int:pk>/delete/", views.EcoProductDeleteView.as_view(), name="ecoproduct_delete"),
    
    # --- 店舗用申請 ---
    path("store/dashboard/", views.store_dashboard, name="store_dashboard"),
    path("store/products/add/", views.StoreEcoProductCreateView.as_view(), name="store_product_create"),
    path("store/products/<int:pk>/edit/", views.StoreEcoProductUpdateView.as_view(), name="store_product_update"),
    path("store/products/<int:pk>/delete/", views.StoreEcoProductDeleteView.as_view(), name="store_product_delete"),
    path("store/products/<int:pk>/delete/", views.StoreEcoProductDeleteView.as_view(), name="store_product_delete"),
    path("store/coupons/add/", views.StoreCouponCreateView.as_view(), name="store_coupon_create"),
    path("store/coupons/<int:pk>/edit/", views.StoreCouponUpdateView.as_view(), name="store_coupon_update"),
    path("store/coupons/<int:coupon_id>/request_delete/", views.store_request_coupon_delete, name="store_request_coupon_delete"),
    
    # --- 承認管理 ---
    path("staff/approvals/", views.approval_list, name="approval_list"),
    path("staff/approvals/approve/<str:type>/<int:id>/", views.approve_item, name="approve_item"),
    path("staff/approvals/reject/<str:type>/<int:id>/", views.reject_item, name="reject_item"),
]