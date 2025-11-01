from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('register/confirm/', views.RegisterConfirmView.as_view(), name='register_confirm'),
    path('register/complete/', views.RegisterCompleteView.as_view(), name='register_complete'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
]
