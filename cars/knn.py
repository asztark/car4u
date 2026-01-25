import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

def find_most_similar_car(cars_queryset, user_vector):
    features = []
    car_ids = []

    active_features = [
        key for key, value in user_vector.items() if value is not None
    ]
    if not active_features:
        raise ValueError("Brak cech liczbowych do obliczenia podobieństwa")

    for car in cars_queryset:
        row = []
        for feature in active_features:
            value = getattr(car, feature)
            if value is None:
                break
            row.append(value)
        else:
            features.append(row)
            car_ids.append(car.id)
    if not features:
        raise ValueError("Brak danych do porównania po filtracji")
    X = np.array(features)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    user_row = np.array([[user_vector[f] for f in active_features]])
    user_scaled = scaler.transform(user_row)

    knn = NearestNeighbors(n_neighbors=1, metric="euclidean")
    knn.fit(X_scaled)

    distance, index = knn.kneighbors(user_scaled)

    return car_ids[index[0][0]], distance[0][0]

import numpy as np
from sklearn.preprocessing import StandardScaler

def find_top_similar_cars(cars_queryset, user_vector, top_n=5):
    """
    Znajduje top N najbardziej podobnych samochodów do user_vector
    używając algorytmu K-Nearest Neighbors.
    
    Args:
        cars_queryset: QuerySet z samochodami do porównania
        user_vector: dict z kluczami: horsepower, total_speed, cars_price, seats
        top_n: liczba wyników do zwrócenia (domyślnie 5)
    
    Returns:
        Lista krotek (car_id, distance) posortowana od najbardziej podobnego
    """
    
    if cars_queryset.count() == 0:
        raise ValueError("Brak samochodów do porównania!")
    
    # Przygotuj dane
    features = ['horsepower', 'total_speed', 'cars_price', 'seats']
    
    # Buduj macierz cech
    car_data = []
    car_ids = []
    
    for car in cars_queryset:
        row = []
        valid = True
        
        for feature in features:
            val = getattr(car, feature)
            try:
                val = float(val) if val is not None else None
                if val is None:
                    valid = False
                    break
                row.append(val)
            except (ValueError, TypeError):
                valid = False
                break
        
        if valid:
            car_data.append(row)
            car_ids.append(car.id)
    
    if len(car_data) == 0:
        raise ValueError("Brak samochodów z kompletnymi danymi!")
    
    # Konwertuj user_vector na listę
    user_row = []
    for feature in features:
        val = user_vector.get(feature)
        if val is None:
            raise ValueError(f"Brak wartości {feature} w wektorze użytkownika!")
        user_row.append(float(val))
    
    # Normalizacja danych
    X = np.array(car_data)
    user_array = np.array([user_row])
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    user_scaled = scaler.transform(user_array)
    
    # Oblicz odległości euklidesowe
    distances = np.sqrt(np.sum((X_scaled - user_scaled) ** 2, axis=1))
    
    # Znajdź top N indeksów
    top_indices = np.argsort(distances)[:top_n]
    
    # Zwróć listę (car_id, distance)
    results = [
        (car_ids[idx], distances[idx]) 
        for idx in top_indices
    ]
    
    return results

