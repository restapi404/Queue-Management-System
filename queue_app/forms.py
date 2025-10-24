from django import forms

class TokenForm(forms.Form):
    customer_name = forms.CharField(
        max_length=100,
        label='Your Name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your name'})
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        label='Phone (optional)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number for SMS'})
    )

class CounterForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        label='Counter Name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Counter name'})
    )