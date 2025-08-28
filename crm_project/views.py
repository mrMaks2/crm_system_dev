from django.shortcuts import render

def home(request):
    user = request.user
    if user.is_authenticated:
        username = (user.get_full_name() or
                    user.first_name or
                    user.last_name or
                    user.username or
                    None)
    else:
        username = None
    return render(request, 'home.html', {'username': username})