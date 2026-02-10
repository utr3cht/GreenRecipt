
from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def check_availability(request):
    """
    ユーザー名またはメールアドレスの重複を確認するAPI
    GET params:
        field: 'username' or 'email'
        value: value to check
    """
    field = request.GET.get('field')
    value = request.GET.get('value')
    
    is_taken = False
    error_message = ""
    
    if field and value:
        if field == 'username':
            if CustomUser.objects.filter(username__iexact=value).exists():
                is_taken = True
                error_message = "このユーザー名は既に使用されています。"
        elif field == 'email':
            if CustomUser.objects.filter(email__iexact=value).exists():
                is_taken = True
                error_message = "このメールアドレスは既に使用されています。"
    
    return JsonResponse({
        'is_taken': is_taken,
        'error_message': error_message
    })
