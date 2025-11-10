from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, TemplateView
from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
import uuid
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .forms import CustomUserCreationForm, CustomUserChangeForm, CustomAuthenticationForm
from .models import CustomUser


class RegisterView(FormView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'

    def form_valid(self, form):
        form_data = form.cleaned_data
        if 'birthday' in form_data and form_data['birthday']:
            form_data['birthday'] = form_data['birthday'].isoformat()
        self.request.session['form_data'] = form_data
        return redirect('accounts:register_confirm')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if 'form_data' in self.request.session:
            kwargs['data'] = self.request.session['form_data']
        return kwargs


class RegisterConfirmView(TemplateView):
    template_name = 'accounts/register_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_data'] = self.request.session.get('form_data')
        return context

    def post(self, request, *args, **kwargs):
        form_data = request.session.get('form_data')
        if not form_data:
            return redirect('accounts:register')

        form = CustomUserCreationForm(form_data)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_verified = False
            user.verification_token = str(uuid.uuid4())
            user.save()

            current_site = get_current_site(self.request)
            mail_subject = 'GreenRecipt: アカウントを有効にしてください'
            message = render_to_string('accounts/account_verification_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': user.verification_token,
            })
            to_email = form.cleaned_data.get('email')
            email = EmailMessage(
                mail_subject, message, to=[to_email]
            )
            email.send()

            del request.session['form_data']
            return redirect('accounts:email_sent')
        else:
            return redirect('accounts:register')


class RegisterCompleteView(TemplateView):
    template_name = 'accounts/register_complete.html'


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = CustomUserChangeForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('core:main_menu')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        # データベースから直接、変更前のユーザー情報を取得
        original_email = CustomUser.objects.get(pk=self.request.user.pk).email
        
        new_email_from_form = form.cleaned_data.get('email')

        # 「新しいメール」と「DBにある元のメール」を比較
        if new_email_from_form and new_email_from_form != original_email:
            # --- メールアドレス変更時の処理 ---
            user_instance = form.save(commit=False)
            user_instance.email = original_email # emailは元の値に戻す
            user_instance.new_email = new_email_from_form # 新しいemailは一時保管場所へ
            user_instance.email_change_token = str(uuid.uuid4())
            user_instance.save()

            # 確認メールを送信
            current_site = get_current_site(self.request)
            mail_subject = 'GreenRecipt: メールアドレスの変更を認証してください'
            message = render_to_string('accounts/email_change_verification_email.html', {
                'user': user_instance,
                'domain': current_site.domain,
                'token': user_instance.email_change_token,
            })
            email = EmailMessage(mail_subject, message, to=[user_instance.new_email])
            email.send()

            messages.success(self.request, '新しいメールアドレスに確認メールを送信しました。メールをご確認の上、変更を完了してください。')
            return HttpResponseRedirect(self.get_success_url())
        
        else:
            # --- メールアドレスが変更されていない時の処理 ---
            return super().form_valid(form)


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    form_class = CustomAuthenticationForm

    def get_success_url(self):
        user = self.request.user
        if user.role in ['admin', 'store']:
            return reverse_lazy('core:staff_index')
        else:
            return reverse_lazy('core:main_menu')


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')


class MyPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')


class MyPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = 'accounts/password_change_done.html'


class ActivateAccountView(TemplateView):
    def get(self, request, uidb64, token, *args, **kwargs):
        User = get_user_model()
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and user.verification_token == token:
            user.is_verified = True
            user.verification_token = None  # Clear the token after successful verification
            user.save()
            # Or a specific success page
            return redirect('accounts:verification_complete')
        else:
            return render(request, 'accounts/activation_invalid.html')

class EmailChangeConfirmView(TemplateView):
    template_name = 'accounts/email_change_complete.html'

    def get(self, request, *args, **kwargs):
        token = self.kwargs.get('token')
        try:
            user = CustomUser.objects.get(email_change_token=token)
        except CustomUser.DoesNotExist:
            return render(request, 'accounts/email_change_invalid.html')

        user.email = user.new_email
        user.new_email = None
        user.email_change_token = None
        user.save()

        return super().get(request, *args, **kwargs)
