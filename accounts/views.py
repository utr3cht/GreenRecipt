from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, TemplateView
from django.views.generic.edit import UpdateView

from .forms import CustomUserCreationForm, CustomUserChangeForm
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
            user = form.save()
            del request.session['form_data']
            return redirect('accounts:register_complete')
        else:
            # If the form is somehow invalid, redirect back to the registration form
            return redirect('accounts:register')


class RegisterCompleteView(TemplateView):
    template_name = 'accounts/register_complete.html'


class ProfileEditView(UpdateView):
    model = CustomUser
    form_class = CustomUserChangeForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('core:main_menu')

    def get_object(self, queryset=None):
        return self.request.user


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')