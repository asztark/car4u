import numpy as np
from collections import defaultdict
from .models import UserCarRating, Car

def calculate_user_similarity(user1_ratings, user2_ratings):
    """
    Oblicza podobieństwo między dwoma użytkownikami używając korelacji Pearsona.
    
    Args:
        user1_ratings: dict {car_id: rating}
        user2_ratings: dict {car_id: rating}
    
    Returns:
        float: współczynnik podobieństwa (-1 do 1, im wyższy tym bardziej podobni)
    """
    # Znajdź wspólnie ocenione auta
    common_cars = set(user1_ratings.keys()) & set(user2_ratings.keys())
    
    if len(common_cars) < 2:  # Potrzeba min 2 wspólnych ocen
        return 0.0
    
    # Pobierz oceny dla wspólnych aut
    ratings1 = [user1_ratings[car_id] for car_id in common_cars]
    ratings2 = [user2_ratings[car_id] for car_id in common_cars]
    
    # Oblicz korelację Pearsona
    mean1 = np.mean(ratings1)
    mean2 = np.mean(ratings2)
    
    numerator = sum((r1 - mean1) * (r2 - mean2) for r1, r2 in zip(ratings1, ratings2))
    denominator1 = np.sqrt(sum((r1 - mean1) ** 2 for r1 in ratings1))
    denominator2 = np.sqrt(sum((r2 - mean2) ** 2 for r2 in ratings2))
    
    if denominator1 == 0 or denominator2 == 0:
        return 0.0
    
    return numerator / (denominator1 * denominator2)


def get_user_ratings_dict(user):
    """Zwraca dict {car_id: rating} dla danego użytkownika"""
    ratings = UserCarRating.objects.filter(user=user)
    return {r.car_id: r.rating for r in ratings}


def recommend_cars_collaborative(user, top_n=5):
    """
    Rekomenduje auta używając collaborative filtering.
    
    Algorytm:
    1. Znajdź użytkowników podobnych do obecnego użytkownika
    2. Zbierz auta wysoko ocenione przez podobnych użytkowników
    3. Filtruj auta już ocenione przez obecnego użytkownika
    4. Zwróć top N aut z najwyższym przewidywanym ratingiem
    
    Args:
        user: obiekt User
        top_n: liczba rekomendacji do zwrócenia
    
    Returns:
        list: [(car, predicted_rating), ...]
    """
    # 1. Pobierz oceny obecnego użytkownika
    current_user_ratings = get_user_ratings_dict(user)
    
    if not current_user_ratings:
        raise ValueError("Użytkownik nie ocenił jeszcze żadnych aut!")
    
    # 2. Znajdź wszystkich innych użytkowników
    all_users = UserCarRating.objects.values_list('user', flat=True).distinct()
    other_users = [u for u in all_users if u != user.id]
    
    if not other_users:
        # Jeśli brak innych użytkowników, zwróć najwyżej ocenione auta z bazy
        return get_top_rated_cars(user, top_n)
    
    # 3. Oblicz podobieństwo do każdego użytkownika
    user_similarities = []
    
    for other_user_id in other_users:
        other_user_ratings = get_user_ratings_dict_by_id(other_user_id)
        similarity = calculate_user_similarity(current_user_ratings, other_user_ratings)
        
        if similarity > 0:  # Tylko pozytywnie skorelowani użytkownicy
            user_similarities.append((other_user_id, similarity))
    
    if not user_similarities:
        # Jeśli brak podobnych użytkowników
        return get_top_rated_cars(user, top_n)
    
    # Sortuj według podobieństwa (malejąco)
    user_similarities.sort(key=lambda x: x[1], reverse=True)
    
    # 4. Zbierz przewidywane oceny dla nieocenionych aut
    car_predictions = defaultdict(list)
    
    # Weź top 10 najbardziej podobnych użytkowników
    for similar_user_id, similarity in user_similarities[:10]:
        similar_user_ratings = get_user_ratings_dict_by_id(similar_user_id)
        
        for car_id, rating in similar_user_ratings.items():
            if car_id not in current_user_ratings:  # Auto jeszcze nieocenione
                # Przewidywana ocena = ocena podobnego użytkownika * jego podobieństwo
                car_predictions[car_id].append(rating * similarity)
    
    # 5. Oblicz średnie przewidywane oceny
    car_scores = []
    for car_id, weighted_ratings in car_predictions.items():
        avg_score = np.mean(weighted_ratings)
        car_scores.append((car_id, avg_score))
    
    # Sortuj według przewidywanej oceny
    car_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 6. Pobierz obiekty Car dla top N
    recommendations = []
    for car_id, score in car_scores[:top_n]:
        try:
            car = Car.objects.get(id=car_id)
            recommendations.append((car, round(score, 2)))
        except Car.DoesNotExist:
            continue
    
    return recommendations


def get_user_ratings_dict_by_id(user_id):
    """Pomocnicza funkcja - zwraca dict ocen dla user_id"""
    ratings = UserCarRating.objects.filter(user_id=user_id)
    return {r.car_id: r.rating for r in ratings}


def get_top_rated_cars(user, top_n=5):
    """
    Fallback: zwraca najlepiej ocenione auta globalnie (jeśli brak danych CF)
    """
    # Pobierz auta już ocenione przez użytkownika
    rated_car_ids = UserCarRating.objects.filter(user=user).values_list('car_id', flat=True)
    
    # Znajdź średnie oceny dla każdego auta
    from django.db.models import Avg
    top_cars = (
        Car.objects
        .exclude(id__in=rated_car_ids)
        .annotate(avg_rating=Avg('usercarrating__rating'))
        .filter(avg_rating__isnull=False)
        .order_by('-avg_rating')[:top_n]
    )
    
    return [(car, car.avg_rating) for car in top_cars]


def get_random_cars_for_quiz(n=10):
    """
    Zwraca losową próbkę n samochodów do oceny w quizie.
    Stara się wybrać różnorodne auta (różne marki, ceny, itp.)
    """
    from django.db.models import Q
    
    # Pobierz różnorodne auta z różnych przedziałów cenowych
    cars = []
    
    # 3 tanie auta (< 100k)
    cheap = list(Car.objects.filter(cars_price__lt=100000).order_by('?')[:3])
    cars.extend(cheap)
    
    # 4 średnie (100k - 200k)
    medium = list(Car.objects.filter(cars_price__gte=100000, cars_price__lt=200000).order_by('?')[:4])
    cars.extend(medium)
    
    # 3 drogie (> 200k)
    expensive = list(Car.objects.filter(cars_price__gte=200000).order_by('?')[:3])
    cars.extend(expensive)
    
    # Jeśli mamy mniej niż n, uzupełnij losowymi
    if len(cars) < n:
        remaining = n - len(cars)
        extra = list(Car.objects.exclude(id__in=[c.id for c in cars]).order_by('?')[:remaining])
        cars.extend(extra)
    
    return cars[:n]
