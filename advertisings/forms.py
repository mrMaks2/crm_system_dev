from django import forms

class CampaignAnalysisForm(forms.Form):

    article = forms.CharField(
        label='Артикул товара',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите артикул товара'
        })
    )

    date_start = forms.DateTimeField(
        input_formats=['%Y-%m-%d'],
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker-input',
            'data-target': '#datetimepicker3',
            'placeholder': 'Введите дату начала фильтрации (Формат YYYY-MM-DD)'
        })
    )
    date_end = forms.DateTimeField(
        input_formats=['%Y-%m-%d'],
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker-input',
            'data-target': '#datetimepicker4',
            'placeholder': 'Введите дату конца фильтрации (Формат YYYY-MM-DD)'
        })
    )