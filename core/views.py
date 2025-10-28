from django.shortcuts import render

def main_menu(request):
    return render(request, "core/main_menu.html")
