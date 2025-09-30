from django import forms

class ProductCardForm(forms.Form):
    article = forms.CharField(
        label='Артикул товара',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите артикул товара'
        })
    )

    CHOICES = (('cab_1', 'Кабинет 1'), ('cab_2', 'Кабинет 2'), ('cab_3', 'Кабинет 3'))
    cabinet = forms.ChoiceField(
        choices=CHOICES, 
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Кабинет'
    )