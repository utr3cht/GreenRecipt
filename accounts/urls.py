from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('register/confirm/', views.RegisterConfirmView.as_view(), name='register_confirm'),
    path('register/complete/', views.RegisterCompleteView.as_view(), name='register_complete'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('profile/password/', views.MyPasswordChangeView.as_view(), name='password_change'),
    path('profile/password/done/', views.MyPasswordChangeDoneView.as_view(), name='password_change_done'),
    path('activate/<uidb64>/<token>/', views.ActivateAccountView.as_view(), name='activate'),
    path('email_sent/', TemplateView.as_view(template_name='accounts/email_sent.html'), name='email_sent'),
    path('verification_complete/', TemplateView.as_view(template_name='accounts/verification_complete.html'), name='verification_complete'),
    path('profile/email_change_confirm/<str:token>/', views.EmailChangeConfirmView.as_view(), name='email_change_confirm'),
]
