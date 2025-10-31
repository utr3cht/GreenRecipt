from django.shortcuts import render

def register(request):
    return render(request, 'accounts/register.html')

def register_confirm(request):
    return render(request, 'accounts/register_confirm.html')

def register_complete(request):
    return render(request, 'accounts/register_complete.html')

def login_view(request):
    return render(request, 'accounts/login.html')

def logout_view(request):
    return render(request, 'accounts/logout.html')