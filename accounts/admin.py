from django.contrib import admin
from .models import CustomUser
from django.utils.translation import gettext_lazy as _

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'is_active', 'is_staff', 'date_joined', 'last_login', 'role', 'store', 'current_points', 'rank', 'updated_at', 'birthday', 'purchased_amount', 'lastmonth_point')
    list_display_links = ('id', 'username')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('email', 'birthday', 'role', 'store', 'current_points', 'rank', 'purchased_amount', 'lastmonth_point', 'current_coupons')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    filter_horizontal = ('groups', 'user_permissions', 'current_coupons')


admin.site.register(CustomUser, CustomUserAdmin)
