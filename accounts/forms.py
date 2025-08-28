from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError

User = get_user_model()

class UserLoginForm(forms.Form):
    username = forms.CharField(label='Логин',
                               widget=forms.TextInput(attrs={
                                   'class': 'form-control',
                                   'placeholder': 'Введите логин'
    }))
    password = forms.CharField(label='Пароль',
                               widget=forms.PasswordInput(attrs={
                                   'class': 'form-control',
                                   'placeholder': 'Введите пароль'
    }))

    # forms.py - обновите clean метод в UserLoginForm
    def clean(self, *args, **kwargs):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username and password:
            qs = User.objects.filter(username=username)
            if not qs.exists():
                raise forms.ValidationError('Такого пользователя не существует')
            
            user = qs.first()
            if not user.is_active:
                raise forms.ValidationError('Ваш аккаунт не активирован. Обратитесь к администратору.')
            
            if not check_password(password, user.password):
                raise forms.ValidationError('Неверный пароль')
                
            user = authenticate(username=username, password=password)
            if not user:
                raise forms.ValidationError('Данный пользователь не активен')
        return super().clean(*args, **kwargs)

class UserRegistrationForm(forms.ModelForm):
    username = forms.CharField(label='Логин',
                               widget=forms.TextInput(attrs={
                                   'class': 'form-control',
                                   'placeholder': 'Введите логин'
    }))
    password = forms.CharField(label='Пароль',
                               widget=forms.PasswordInput(attrs={
                                   'class': 'form-control',
                                   'placeholder': 'Введите пароль'
    }))
    password2 = forms.CharField(label='Повторный пароль',
                               widget=forms.PasswordInput(attrs={
                                   'class': 'form-control',
                                   'placeholder': 'Повторно введите пароль'
    }))

    class Meta:
        model = User
        fields = ('username',)

    def clean_password2(self):
        data = self.cleaned_data
        if data['password'] != data['password2']:
            raise forms.ValidationError('Пароли не совпадают')
        return data['password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_active = False
        if commit:
            user.save()
        return user