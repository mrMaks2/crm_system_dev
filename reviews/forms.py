from django import forms

class ReviewForm(forms.Form):
    
    CHOICES = (('prod_arg_form', 'Артикул'), ('date_form', 'Дата'))
    my_dropdown = forms.ChoiceField(choices=CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

class HomeForm(forms.Form):

    article_number = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите артикул товара'
        })
    )

class DateForm(forms.Form):

    date_start = forms.DateTimeField(
        input_formats=['%Y-%m-%dT%H:%M:%S.%fZ', '%d/%m/%Y %I:%M %p'],
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker-input',
            'data-target': '#datetimepicker1'
        })
    )
    date_end = forms.DateTimeField(
        input_formats=['%Y-%m-%dT%H:%M:%S.%fZ', '%d/%m/%Y %I:%M %p'],
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker-input',
            'data-target': '#datetimepicker2'
        })
    )

class ReviewsCheckingForm(forms.Form):

    review_example = forms.CharField(
        label='Пример отзыва',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пример отзыва для проверки'
        })
    )
    article = forms.CharField(
        label='Артикул товара',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите артикул товара, с отзывами которого необходимо сравнить'
        })
    )