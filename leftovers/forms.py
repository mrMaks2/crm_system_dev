from django import forms

class StocksOrdersForm(forms.Form):
    report_type = forms.ChoiceField(
        choices=[
            ('stocks', 'Остатки по складам'), 
            ('stocks_by_cluster', 'Остатки по кластерам'),
            ('orders', 'Заказы'), 
            ('needs', 'Потребности'), 
            ('turnover', 'Оборачиваемость')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='stocks'
    )
    
    cab_num = forms.ChoiceField(
        choices=[(1, '1 кабинет'), (2, '2 кабинет'), (3, '3 кабинет')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial=1
    )