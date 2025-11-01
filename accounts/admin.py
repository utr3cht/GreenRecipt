from django.contrib import admin
from .models import CustomUser
# Register your models here.


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'is_active', 'is_staff', 'date_joined', 'last_login', 'role', 'store', 'current_points', 'rank', 'updated_at', 'birthday', 'purchased_amount', 'lastmonth_point')
    list_display_links = ('id', 'username')


admin.site.register(CustomUser, CustomUserAdmin)
