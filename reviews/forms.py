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
        input_formats=['%d/%m/%Y %H:%M'],
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker-input',
            'data-target': '#datetimepicker1',
            'placeholder': 'Введите дату начала фильтрации (Формат DD/MM/YYYY HH:mm)'
        })
    )
    date_end = forms.DateTimeField(
        input_formats=['%d/%m/%Y %H:%M'],
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker-input',
            'data-target': '#datetimepicker2',
            'placeholder': 'Введите дату конца фильтрации (Формат DD/MM/YYYY HH:mm)'
        })
    )


class ReviewsCheckingForm(forms.Form):
    article = forms.CharField(
        label='Артикул товара',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите артикул товара, с отзывами которого необходимо сравнить'
        })
    )
    
    def __init__(self, *args, **kwargs):
        extra_fields = kwargs.pop('extra', 1)
        super(ReviewsCheckingForm, self).__init__(*args, **kwargs)
        
        for i in range(extra_fields):
            self.fields[f'review_example_{i}'] = forms.CharField(
                label=f'Отзыв №{i+1}',
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Введите текст отзыва для проверки'
                }),
                required=False
            )

    @property
    def field_count(self):
        return len([f for f in self.fields if 'review_example_' in f])