from django.shortcuts import render

def home(request):
    username = request.user.get_full_name() or request.user.first_name or request.user.last_name or request.user.username
    return render(request, 'home.html', {'username': username})