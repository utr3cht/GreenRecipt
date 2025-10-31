from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('register/confirm/', views.register_confirm, name='register_confirm'),
    path('register/complete/', views.register_complete, name='register_complete'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
