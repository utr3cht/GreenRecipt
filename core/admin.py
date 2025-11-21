from django.contrib import admin
from .models import EcoProduct, Coupon, Receipt, Store

class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('user', 'store', 'scanned_at')
    list_filter = ('user', 'store', 'scanned_at')
    search_fields = ('user__username',)

admin.site.register(Receipt, ReceiptAdmin)
admin.site.register(EcoProduct)
admin.site.register(Coupon)
