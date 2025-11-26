from django.contrib import admin
from .models import (
    Store, Receipt, Product, ReceiptItem, Inquiry, 
    Coupon, CouponUsage, Report, Announcement, EcoProduct
)

class StoreAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'category', 'tel', 'address')
    search_fields = ('store_name', 'address')
    list_filter = ('category',)

class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('user', 'store', 'scanned_at', 'total_amount')
    list_filter = ('scanned_at', 'store')
    search_fields = ('user__username', 'store__store_name')

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class ReceiptItemAdmin(admin.ModelAdmin):
    list_display = ('receipt', 'product', 'quantity', 'price')
    list_filter = ('product',)

class InquiryAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'created_at', 'is_replied')
    list_filter = ('status', 'is_replied', 'created_at')
    search_fields = ('subject', 'body_text', 'user__username', 'user__email')

class CouponAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'discount_value', 'requirement')
    list_filter = ('type',)
    search_fields = ('title', 'description')

class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'coupon', 'store', 'used_at')
    list_filter = ('used_at', 'store', 'coupon')
    search_fields = ('user__username', 'coupon__title')

class ReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'score', 'generated_at')
    list_filter = ('generated_at',)
    search_fields = ('user__username',)

class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title', 'content')

class EcoProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'points', 'jan_code')
    search_fields = ('name', 'jan_code')

admin.site.register(Store, StoreAdmin)
admin.site.register(Receipt, ReceiptAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ReceiptItem, ReceiptItemAdmin)
admin.site.register(Inquiry, InquiryAdmin)
admin.site.register(Coupon, CouponAdmin)
admin.site.register(CouponUsage, CouponUsageAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Announcement, AnnouncementAdmin)
admin.site.register(EcoProduct, EcoProductAdmin)
