from django import forms

class ReviewForm(forms.Form):
    CHOICES = [('prod_arg_form', 'Артикул'), ('date_form', 'Дата')]
    my_dropdown = forms.ChoiceField(choices=CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

class HomeForm(forms.Form):
    article_number = forms.IntegerField( widget=forms.NumberInput(attrs={
                                         'class': 'form-control',
                                         'placeholder': 'Введите артикул товара'
    }))