from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import Car, UserCarRating
from .forms import CarFilterForm, CarSelectForm, CompanyConstraintsForm
import pandas as pd
from .knn import find_most_similar_car
from .collaborative_filtering import get_random_cars_for_quiz, recommend_cars_collaborative
from .utils import apply_filters, build_user_vector

def index(request):
    qs = Car.objects.all()

    # przygotowujemy unikalne wartości dla pól wyboru
    companies = sorted(set(Car.objects.exclude(company_name__isnull=True).values_list('company_name', flat=True)))
    car_names = sorted(set(Car.objects.exclude(car_name__isnull=True).values_list('car_name', flat=True)))
    engines = sorted(set(Car.objects.exclude(engine__isnull=True).values_list('engine', flat=True)))

    # utworzenie formularza i ustawienie choices dynamicznie
    form = CarFilterForm(request.GET or None)
    form.fields['company_name'].choices = [(c,c) for c in companies]
    form.fields['car_name'].choices = [(c,c) for c in car_names]
    form.fields['engine'].choices = [(c,c) for c in engines]

    filtered = False
    if form.is_valid():
        data = form.cleaned_data
        # filtrowanie po wielu polach
        if data.get('company_name'):
            qs = qs.filter(company_name__in=data['company_name'])
            filtered = True
        if data.get('car_name'):
            qs = qs.filter(car_name__in=data['car_name'])
            filtered = True
        if data.get('engine'):
            qs = qs.filter(engine__in=data['engine'])
            filtered = True
        if data.get('min_power') is not None:
            qs = qs.filter(horsepower__gte=data['min_power'])
            filtered = True
        if data.get('max_power') is not None:
            qs = qs.filter(horsepower__lte=data['max_power'])
            filtered = True
        if data.get('min_speed') is not None:
            qs = qs.filter(total_speed__gte=data['min_speed'])
            filtered = True
        if data.get('max_speed') is not None:
            qs = qs.filter(total_speed__lte=data['max_speed'])
            filtered = True
        if data.get('min_price') is not None:
            qs = qs.filter(cars_price__gte=data['min_price'])
            filtered = True
        if data.get('max_price') is not None:
            qs = qs.filter(cars_price__lte=data['max_price'])
            filtered = True
        if data.get('fuel_type'):
            if data['fuel_type'] != '':
                qs = qs.filter(fuel_type=data['fuel_type'])
                filtered = True
        if data.get('seats'):
            qs = qs.filter(seats__icontains=data['seats'])
            filtered = True

    # paginacja / limit można dodać tutaj - dla prostoty pokażemy wszystkie
    results = qs.order_by('company_name')[:1000]  # limit safety

    context = {
        'form': form,
        'results': results,
        'filtered': filtered,
    }
    return render(request, 'cars/index.html', context)


def download_csv(request):
    qs = Car.objects.all()
    
    companies = sorted(Car.objects.values_list('company_name', flat=True).distinct())
    car_names = sorted(Car.objects.values_list('car_name', flat=True).distinct())
    
    engines_qs = Car.objects.all()
    if request.GET.get("company_name"):
        engines_qs = engines_qs.filter(company_name=request.GET.get("company_name"))
    if request.GET.get("car_name"):
        engines_qs = engines_qs.filter(car_name=request.GET.get("car_name"))
    engines = sorted(engines_qs.values_list("engine", flat=True).distinct())
    
    form = CarFilterForm(request.GET or None)
    form.fields['company_name'].choices = [(c, c) for c in companies if c]
    form.fields['car_name'].choices = [(c, c) for c in car_names if c]
    form.fields['engine'].choices = [("", "Wszystkie")] + [(c, c) for c in engines if c]
    
    # ✅ TA SAMA LOGIKA FILTROWANIA CO W search()
    if form.is_valid():
        data = form.cleaned_data
        
        if data.get('company_name'):
            qs = qs.filter(company_name__iexact=data['company_name'])
        if data.get('car_name'):
            qs = qs.filter(car_name__iexact=data['car_name'])
        
        engine_list = data.get('engine')
        if engine_list:
            engine_list = [e for e in engine_list if e]
            if engine_list:
                qs = qs.filter(engine__in=engine_list)
        
        if data.get('min_power') is not None:
            qs = qs.filter(horsepower__gte=data['min_power'])
        if data.get('max_power') is not None:
            qs = qs.filter(horsepower__lte=data['max_power'])
        if data.get('min_speed') is not None:
            qs = qs.filter(total_speed__gte=data['min_speed'])
        if data.get('max_speed') is not None:
            qs = qs.filter(total_speed__lte=data['max_speed'])
        if data.get('min_price') is not None:
            qs = qs.filter(cars_price__gte=data['min_price'])
        if data.get('max_price') is not None:
            qs = qs.filter(cars_price__lte=data['max_price'])
        if data.get('fuel_type'):
            qs = qs.filter(fuel_type=data['fuel_type'])
        if data.get('seats'):
            qs = qs.filter(seats=data['seats'])
    
    # ✅ Tworzenie CSV
    if qs.exists():
        df = pd.DataFrame(list(qs.values(
            'company_name', 'car_name', 'engine', 'horsepower', 
            'total_speed', 'cars_price', 'fuel_type', 'seats'
        )))
        
        # Polskie nazwy kolumn
        df.columns = ['Marka', 'Model', 'Silnik', 'Moc (KM)', 
                      'Prędkość (km/h)', 'Cena (PLN)', 'Paliwo', 'Miejsca']
    else:
        df = pd.DataFrame(columns=['Marka', 'Model', 'Silnik', 'Moc (KM)', 
                                   'Prędkość (km/h)', 'Cena (PLN)', 'Paliwo', 'Miejsca'])
    
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    
    response = HttpResponse(csv, content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="wyniki_filtrowania.csv"'
    
    return response

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'cars/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'cars/login.html', {'form': form})

def logout_view(request):
    auth_logout(request)
    return redirect('home')

def home(request):
    return render(request, "cars/home.html")

from django.core.paginator import Paginator


def search(request):
    if 'download_csv' in request.GET:
        return download_csv(request)
    qs = Car.objects.all()

    companies = sorted(Car.objects.values_list('company_name', flat=True).distinct())
    car_names = sorted(Car.objects.values_list('car_name', flat=True).distinct())
    engines_qs = Car.objects.all()

    if request.GET.get("company_name"):
        engines_qs = engines_qs.filter(company_name=request.GET.get("company_name"))

    if request.GET.get("car_name"):
        engines_qs = engines_qs.filter(car_name=request.GET.get("car_name"))

    engines = sorted(engines_qs.values_list("engine", flat=True).distinct())


    form = CarFilterForm(request.GET or None)
    form.fields['company_name'].choices = [(c, c) for c in companies if c]
    form.fields['car_name'].choices = [(c, c) for c in car_names if c]
    form.fields['engine'].choices = [("", "Wszystkie")] + [(c, c) for c in engines if c]

    filtered = False

    print("IS VALID:", form.is_valid())
    print("FORM ERRORS:", form.errors)

    if form.is_valid():
        data = form.cleaned_data
        print("CLEANED DATA:", data)

        if data.get('company_name'):
            qs = qs.filter(company_name__iexact=data['company_name'])
            filtered = True
        if data.get('car_name'):
            qs = qs.filter(car_name__iexact=data['car_name'])
            filtered = True

        engine_list = data.get('engine')

        if engine_list:
            engine_list = [e for e in engine_list if e]  # usuwa ""

            if engine_list:
                qs = qs.filter(engine__in=engine_list)
                filtered = True

        if data.get('min_power') is not None:
            qs = qs.filter(horsepower__gte=data['min_power'])
            filtered = True
        if data.get('max_power') is not None:
            qs = qs.filter(horsepower__lte=data['max_power'])
            filtered = True
        if data.get('min_speed') is not None:
            qs = qs.filter(total_speed__gte=data['min_speed'])
            filtered = True
        if data.get('max_speed') is not None:
            qs = qs.filter(total_speed__lte=data['max_speed'])
            filtered = True
        if data.get('min_price') is not None:
            qs = qs.filter(cars_price__gte=data['min_price'])
            filtered = True
        if data.get('max_price') is not None:
            qs = qs.filter(cars_price__lte=data['max_price'])
            filtered = True
        if data.get('fuel_type'):
            qs = qs.filter(fuel_type=data['fuel_type'])
            filtered = True
        if data.get('seats'):
            qs = qs.filter(seats=data['seats'])
            filtered = True

    print("FINAL QS:", qs.query)


    paginator = Paginator(qs, 10)  # 10 wyników na stronę
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "cars/search.html", {
    "form": form,
    "results": page_obj,
    "filtered": filtered,
    "page_obj": page_obj,
})


def recommend_car(request):
    from .knn import find_top_similar_cars  # Nowa funkcja zwracająca top 5
    
    constraints_form = CompanyConstraintsForm()
    select_form = CarSelectForm()
    
    result_cars = []  # Lista top 5 aut
    error = None
    
    company = request.POST.get("company_name")
    model = request.POST.get("car_name")
    
    # Inicjalizacja formularzy
    if request.method == "POST":
        constraints_form = CompanyConstraintsForm(request.POST)
        
        # Dynamiczne ustawienie wyborów dla marki
        company_choices = sorted(set(
            Car.objects.exclude(company_name__isnull=True)
            .values_list('company_name', flat=True)
        ))
        select_form.fields['company_name'].choices = [(c, c) for c in company_choices]
        
        # Dynamiczne ustawienie wyborów dla modelu
        if company:
            model_choices = sorted(set(
                Car.objects.filter(company_name=company)
                .values_list('car_name', flat=True)
            ))
            select_form.fields['car_name'].choices = [(m, m) for m in model_choices]
    
    # Przetwarzanie rekomendacji
    if company and model and constraints_form.is_valid():
        try:
            # 1. Znajdź auto bazowe
            base_car = Car.objects.filter(
                company_name=company, 
                car_name=model
            ).first()
            
            if not base_car:
                raise ValueError("❌ Nie znaleziono wybranego auta!")
            
            # 2. Przygotuj wektor użytkownika (z auta bazowego)
            user_vector = {}
            for field in ["horsepower", "total_speed", "cars_price", "seats"]:
                val = getattr(base_car, field)
                try:
                    user_vector[field] = float(val) if val is not None else None
                except (ValueError, TypeError):
                    user_vector[field] = None
            
            # 3. Zastosuj ograniczenia firmowe
            cars_queryset = Car.objects.exclude(id=base_car.id)
            constraints = constraints_form.cleaned_data
            
            if constraints.get('max_price') is not None:
                cars_queryset = cars_queryset.filter(
                    cars_price__lte=constraints['max_price']
                )
            if constraints.get('min_price') is not None:
                cars_queryset = cars_queryset.filter(
                    cars_price__gte=constraints['min_price']
                )
            if constraints.get('max_horsepower') is not None:
                cars_queryset = cars_queryset.filter(
                    horsepower__lte=constraints['max_horsepower']
                )
            if constraints.get('min_horsepower') is not None:
                cars_queryset = cars_queryset.filter(
                    horsepower__gte=constraints['min_horsepower']
                )
            if constraints.get('fuel_type'):
                cars_queryset = cars_queryset.filter(
                    fuel_type=constraints['fuel_type']
                )
            if constraints.get('max_seats') is not None:
                cars_queryset = cars_queryset.filter(
                    seats__lte=constraints['max_seats']
                )
            if constraints.get('min_seats') is not None:
                cars_queryset = cars_queryset.filter(
                    seats__gte=constraints['min_seats']
                )
            
            # Sprawdź czy są dostępne auta po filtracji
            if cars_queryset.count() == 0:
                raise ValueError(
                    "⚠️ Brak aut spełniających ograniczenia firmowe! "
                    "Spróbuj złagodzić kryteria."
                )
            
            # 4. Znajdź TOP 5 podobnych aut
            top_results = find_top_similar_cars(cars_queryset, user_vector, top_n=5)
            
            # 5. Pobierz obiekty Car z wynikami
            for car_id, distance in top_results:
                car = Car.objects.get(id=car_id)
                result_cars.append({
                    'car': car,
                    'distance': distance
                })
        
        except Exception as e:
            error = str(e)
    
    return render(request, "cars/recommend.html", {
        "constraints_form": constraints_form,
        "select_form": select_form,
        "result_cars": result_cars,
        "error": error
    })

@login_required
def quiz_view(request):
    """
    Widok quizu - użytkownik ocenia samochody, a następnie dostaje rekomendacje
    """
    # Sprawdź czy użytkownik już oceniał auta
    user_ratings_count = UserCarRating.objects.filter(user=request.user).count()
    
    # ETAP 1: QUIZ - Ocenianie samochodów
    if request.method == "POST" and 'submit_ratings' in request.POST:
        # Zapisz oceny użytkownika
        saved_count = 0
        
        for key, value in request.POST.items():
            if key.startswith('rating_'):
                car_id = int(key.split('_')[1])
                rating = int(value)
                
                # Zapisz lub zaktualizuj ocenę
                UserCarRating.objects.update_or_create(
                    user=request.user,
                    car_id=car_id,
                    defaults={'rating': rating}
                )
                saved_count += 1
        
        # Przekieruj do wyników
        return redirect('quiz_results')
    
    # ETAP 2: Generuj quiz (jeśli użytkownik nie ocenił jeszcze lub chce powtórzyć)
    if 'reset_quiz' in request.GET or user_ratings_count == 0:
        # Pobierz losowe auta do oceny
        quiz_cars = get_random_cars_for_quiz(n=10)
        
        # Zapisz ID aut w sesji (żeby zachować te same auta przy odświeżeniu)
        request.session['quiz_car_ids'] = [car.id for car in quiz_cars]
        
        return render(request, 'cars/quiz.html', {
            'quiz_cars': quiz_cars,
            'step': 'rating'
        })
    
    # Jeśli użytkownik ma już oceny, przekieruj do wyników
    return redirect('quiz_results')


@login_required
def quiz_results_view(request):
    """Wyświetla rekomendacje na podstawie collaborative filtering"""
    
    user_ratings_count = UserCarRating.objects.filter(user=request.user).count()
    
    if user_ratings_count == 0:
        # Użytkownik nie wypełnił jeszcze quizu
        return redirect('quiz')
    
    try:
        # Generuj rekomendacje używając collaborative filtering
        recommendations = recommend_cars_collaborative(request.user, top_n=5)
        
        # Pobierz oceny użytkownika do wyświetlenia
        user_ratings = UserCarRating.objects.filter(user=request.user).order_by('-rating')[:10]
        
        return render(request, 'cars/quiz_results.html', {
            'recommendations': recommendations,
            'user_ratings': user_ratings,
            'total_ratings': user_ratings_count
        })
    
    except ValueError as e:
        return render(request, 'cars/quiz_results.html', {
            'error': str(e),
            'user_ratings': UserCarRating.objects.filter(user=request.user).order_by('-rating')
        })
    
from django.http import JsonResponse


def get_models_by_brand(request):
    brand = request.GET.get('company_name')

    models = []
    if brand:
        models = (
            Car.objects
            .filter(company_name=brand)
            .values_list('car_name', flat=True)
            .distinct()
            .order_by('car_name')
        )

    return JsonResponse(list(models), safe=False)

from django.http import JsonResponse


def get_engines(request):
    brand = request.GET.get("company_name")
    model = request.GET.get("car_name")

    engines = Car.objects.all()

    if brand:
        engines = engines.filter(company_name=brand)

    if model:
        engines = engines.filter(car_name=model)

    engines = (
        engines
        .values_list("engine", flat=True)
        .distinct()
        .order_by("engine")
    )

    return JsonResponse(list(engines), safe=False)



