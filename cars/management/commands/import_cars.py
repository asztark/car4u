from django.core.management.base import BaseCommand
import pandas as pd
import numpy as np
import re
from cars.models import Car
from pathlib import Path
from django.conf import settings

class Command(BaseCommand):
    help = 'Import Cars Datasets 2025.csv into Car model'

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR)
        csv_path = base / 'data' / 'Cars Datasets 2025.csv'
        if not csv_path.exists():
            self.stdout.write(self.style.ERROR(f'Plik nie istnieje: {csv_path}'))
            return

        df = pd.read_csv(csv_path, encoding='cp1252')

        # Jeśli chcesz usunąć niepotrzebne kolumny (jak w prototyp.py)
        for col in ["CC/Battery Capacity", "Performance(0 - 100 )KM/H", "Torque"]:
            if col in df.columns:
                df = df.drop(columns=[col])

        # Czyszczenie cen (kopiowane podejście z prototyp.py)
        df['Cars Prices'] = df.get('Cars Prices', pd.Series([np.nan]*len(df)))
        df['Cars Prices'] = df['Cars Prices'].replace({'\$': '', ',': '', ' ': ''}, regex=True)

        def clean_price(value):
            if '-' in str(value):
                price_range = re.findall(r'\d+', str(value))
                if len(price_range) == 2:
                    return (int(price_range[0]) + int(price_range[1])) / 2
            try:
                return float(value)
            except:
                return np.nan

        df['Cars Prices'] = df['Cars Prices'].apply(clean_price)
        df['Cars Prices'] = pd.to_numeric(df['Cars Prices'], errors='coerce')

        # HorsePower parsing
        def extract_hp(value):
            nums = re.findall(r'\d+', str(value))
            if not nums: return np.nan
            nums = list(map(int, nums))
            return sum(nums)/len(nums)
        df['HorsePower_num'] = df.get('HorsePower', '').apply(extract_hp)

        # Total Speed parsing
        if 'Total Speed' in df.columns:
            df['speed_num'] = df['Total Speed'].astype(str).str.replace(r'\D', '', regex=True)
            df['speed_num'] = pd.to_numeric(df['speed_num'], errors='coerce')
        else:
            df['speed_num'] = np.nan

        def clean_seats(value):
            """Konwertuje zapis typu '2+2' lub '0-17' na liczbę całkowitą"""
            value_str = str(value)
            # Jeśli jest przedział np. 0-17, weź średnią
            if '-' in value_str:
                nums = re.findall(r'\d+', value_str)
                if len(nums) == 2:
                    return int((int(nums[0]) + int(nums[1])) / 2)
            # Jeśli jest zapis typu 2+2, zsumuj liczby
            if '+' in value_str:
                nums = re.findall(r'\d+', value_str)
                return sum(int(n) for n in nums)
            # Jeśli zwykła liczba
            try:
                return int(value_str)
            except:
                return None



        # Zapis do bazy
        created = 0
        for _, row in df.iterrows():
            car = Car(
                company_name = row.get('Company Names'),
                car_name = row.get('Cars Names'),
                engine = row.get('Engines'),
                horsepower = float(row.get('HorsePower_num')) if not pd.isna(row.get('HorsePower_num')) else None,
                total_speed = int(row.get('speed_num')) if not pd.isna(row.get('speed_num')) else None,
                cars_price = float(row.get('Cars Prices')) if not pd.isna(row.get('Cars Prices')) else None,
                fuel_type = row.get('Fuel Types'),
                seats = clean_seats(row.get('Seats')),

            )
            car.save()
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Zaimportowano {created} rekordów.'))
