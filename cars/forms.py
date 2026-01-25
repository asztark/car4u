from django import forms
from .models import Car

class CarFilterForm(forms.Form):
    company_name = forms.ChoiceField(required=False)
    car_name = forms.ChoiceField(required=False, choices=[], label="Model")
    engine = forms.MultipleChoiceField(required=False)
    min_power = forms.FloatField(required=False)
    max_power = forms.FloatField(required=False)
    min_speed = forms.IntegerField(required=False)
    max_speed = forms.IntegerField(required=False)
    min_price = forms.FloatField(required=False)
    max_price = forms.FloatField(required=False)
    fuel_type = forms.ChoiceField(required=False, choices=[('', 'Wszystkie'), ('Petrol','Petrol'),('Diesel','Diesel'),('Electric','Electric'),('Hybrid','Hybrid'),('plug in hybrid','plug in hybrid')])
    seats = forms.IntegerField(required=False)

class CarSelectForm(forms.Form):
    company_name = forms.ChoiceField(label="Marka")
    car_name = forms.ChoiceField(label="Model", required=False)

    def __init__(self, *args, company_name=None, **kwargs):
        super().__init__(*args, **kwargs)

        # MARKI
        companies = (
            Car.objects
            .values_list("company_name", flat=True)
            .distinct()
            .order_by("company_name")
        )
        self.fields["company_name"].choices = [
            (c, c) for c in companies if c
        ]

        # MODELE (dopiero po wyborze marki)
        if company_name:
            models = (
                Car.objects
                .filter(company_name=company_name)
                .values_list("car_name", flat=True)
                .distinct()
                .order_by("car_name")
            )
            self.fields["car_name"].choices = [
                (m, m) for m in models if m
            ]
        else:
            self.fields["car_name"].choices = []

# 🆕 NOWY FORMULARZ - Ograniczenia firmowe
class CompanyConstraintsForm(forms.Form):
    """Formularz dla ograniczeń firmowych stosowanych w rekomendacji"""
    
    max_price = forms.FloatField(
        required=False,
        label="Maksymalna cena",
        widget=forms.NumberInput(attrs={'placeholder': 'np. 200000'})
    )
    min_price = forms.FloatField(
        required=False,
        label="Minimalna cena",
        widget=forms.NumberInput(attrs={'placeholder': 'np. 50000'})
    )
    max_horsepower = forms.FloatField(
        required=False,
        label="Maksymalna moc (KM)",
        widget=forms.NumberInput(attrs={'placeholder': 'np. 300'})
    )
    min_horsepower = forms.FloatField(
        required=False,
        label="Minimalna moc (KM)",
        widget=forms.NumberInput(attrs={'placeholder': 'np. 100'})
    )
    fuel_type = forms.ChoiceField(
        required=False,
        label="Typ paliwa",
        choices=[
            ('', 'Dowolny'),
            ('Petrol', 'Benzyna'),
            ('Diesel', 'Diesel'),
            ('Electric', 'Elektryczny'),
            ('Hybrid', 'Hybrydowy'),
            ('plug in hybrid', 'Plug-in Hybrid')
        ]
    )
    max_seats = forms.IntegerField(
        required=False,
        label="Maksymalna liczba miejsc",
        widget=forms.NumberInput(attrs={'placeholder': 'np. 5'})
    )
    min_seats = forms.IntegerField(
        required=False,
        label="Minimalna liczba miejsc",
        widget=forms.NumberInput(attrs={'placeholder': 'np. 2'})
    )
