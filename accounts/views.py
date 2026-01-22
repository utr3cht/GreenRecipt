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
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .forms import CustomUserCreationForm, CustomUserChangeForm, CustomAuthenticationForm
from .forms import CustomUserCreationForm, CustomUserChangeForm, CustomAuthenticationForm
from .models import CustomUser
import random
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


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
            context = {
                'user': user,
                'domain': current_site.domain,
                'protocol': request.scheme,  # プロトコルを追加 (http/https)
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': user.verification_token,
            }
            
            # テキスト/HTMLコンテンツのレンダリング
            text_content = render_to_string('accounts/account_verification_email.txt', context)
            html_content = render_to_string('accounts/account_verification_email.html', context)
            
            to_email = form.cleaned_data.get('email')
            
            # メール作成
            email = EmailMultiAlternatives(
                mail_subject,
                text_content,
                to=[to_email]
            )
            # HTML版の添付
            email.attach_alternative(html_content, "text/html")
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
        # 変更前の情報取得
        original_email = CustomUser.objects.get(pk=self.request.user.pk).email
        
        new_email_from_form = form.cleaned_data.get('email')

        # メール変更チェック
        if new_email_from_form and new_email_from_form != original_email:
            # メール変更処理
            user_instance = form.save(commit=False)
            user_instance.email = original_email # 元のメールを保持
            user_instance.new_email = new_email_from_form # 新メールを一時保存
            user_instance.email_change_token = str(uuid.uuid4())
            user_instance.save()

            # 確認メール送信
            current_site = get_current_site(self.request)
            mail_subject = 'GreenRecipt: メールアドレスの変更を認証してください'
            context = {
                'user': user_instance,
                'domain': current_site.domain,
                'protocol': self.request.scheme, # プロトコルを追加
                'token': user_instance.email_change_token,
            }

            # Render plain text and HTML content
            text_content = render_to_string('accounts/email_change_verification_email.txt', context)
            html_content = render_to_string('accounts/email_change_verification_email.html', context)

            # Create the email message
            email = EmailMultiAlternatives(
                mail_subject,
                text_content,
                to=[user_instance.new_email]
            )
            # Attach the HTML version
            email.attach_alternative(html_content, "text/html")
            email.send()

            messages.success(self.request, '新しいメールアドレスに確認メールを送信しました。メールをご確認の上、変更を完了してください。')
            return HttpResponseRedirect(self.get_success_url())
        
        else:
            # メール変更なし
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
            user.verification_token = None  # 認証完了後にトークン消去
            user.save()
            # 成功ページへ
            return redirect('accounts:verification_complete')
        else:
            return render(request, 'accounts/activation_invalid.html')

class EmailChangeConfirmView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/email_change_success.html'

    def get(self, request, *args, **kwargs):
        token = kwargs.get('token')
        try:
            user = CustomUser.objects.get(email_change_token=token)
            if user.new_email:
                user.email = user.new_email
                user.new_email = None
                user.email_change_token = None
                user.save()
                messages.success(request, 'メールアドレスの変更が完了しました。')
            else:
                messages.error(request, '無効なリクエストです。')
                return redirect('core:index') # または適切なページ
        except CustomUser.DoesNotExist:
            messages.error(request, '無効なトークンです。')
            return redirect('core:index')

        return super().get(request, *args, **kwargs)


class RequestWithdrawalView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/request_withdrawal.html'

    def post(self, request, *args, **kwargs):
        # 現在のパスワード確認
        password = request.POST.get('password')
        if not password:
            messages.error(request, 'パスワードを入力してください。')
            return render(request, self.template_name)
        
        if not request.user.check_password(password):
            messages.error(request, 'パスワードが正しくありません。')
            return render(request, self.template_name)

        # 確認コード生成
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        request.user.withdrawal_code = code
        request.user.withdrawal_code_expires_at = timezone.now() + timedelta(minutes=10) # 10分有効
        request.user.save()

        # メール送信
        subject = '【GreenRecipt】退会確認コード'
        message = f"""
        GreenReciptをご利用いただきありがとうございます。

        退会手続きを進めるには、以下の確認コードを入力画面に入力してください。

        確認コード: {code}

        ※このコードは10分間有効です。
        ※お心当たりのない場合は、そのまま破棄してください。
        """
        
        # コンソール/メール送信（設定依存）
        if settings.SEND_EMAIL:
            try:
                email = EmailMessage(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [request.user.email]
                )
                email.send()
            except Exception as e:
                logger.error(f"Failed to send withdrawal email: {e}")
                messages.error(request, "メール送信に失敗しました。時間をおいて再度お試しください。")
                return redirect('accounts:request_withdrawal')
        else:
            print(f"--- Withdrawal Code for {request.user.email}: {code} ---")
        
        messages.info(request, '確認コードをメールで送信しました。')
        return redirect('accounts:confirm_withdrawal')


class ConfirmWithdrawalView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/confirm_withdrawal.html'

    def post(self, request, *args, **kwargs):
        code = request.POST.get('withdrawal_code')
        
        if not code:
            messages.error(request, '確認コードを入力してください。')
            return render(request, self.template_name)

        if not request.user.withdrawal_code or str(request.user.withdrawal_code) != str(code):
            messages.error(request, '確認コードが正しくありません。')
            return render(request, self.template_name)
        
        if not request.user.withdrawal_code_expires_at or request.user.withdrawal_code_expires_at < timezone.now():
            messages.error(request, '確認コードの有効期限が切れています。再度申請してください。')
            return render(request, self.template_name)

        # 退会処理
        try:
            # 物理削除または論理削除。ここではユーザー要望に従い「退会」＝削除とするが、
            # 関連データへの影響を考慮し、論理削除(is_active=False)の方が安全かも知れないが、
            # 特に指定がないためdelete()する。
            user = request.user
            # ログアウトしてから削除しないとセッションが残る場合があるが、削除すれば消えるはず
            from django.contrib.auth import logout
            logout(request)
            user.delete()
            messages.success(request, '退会処理が完了しました。ご利用ありがとうございました。')
            return redirect('core:index') # トップページへ
        except Exception as e:
            logger.error(f"Failed to delete user {request.user.id}: {e}")
            messages.error(request, '退会処理中にエラーが発生しました。管理者にお問い合わせください。')
            return redirect('accounts:confirm_withdrawal')
