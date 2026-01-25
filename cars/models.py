from django.db import models
from django.contrib.auth.models import User

class Car(models.Model):
    company_name = models.CharField(max_length=200, null=True, blank=True)
    car_name = models.CharField(max_length=300, null=True, blank=True)
    engine = models.CharField(max_length=200, null=True, blank=True)
    horsepower = models.FloatField(null=True, blank=True)
    total_speed = models.IntegerField(null=True, blank=True)
    cars_price = models.FloatField(null=True, blank=True)
    fuel_type = models.CharField(max_length=100, null=True, blank=True)
    seats = models.IntegerField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.company_name} {self.car_name}"

class UserCarRating(models.Model):
    """Oceny samochodów wystawione przez użytkowników"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    rating = models.IntegerField()  # Skala 1-5
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'car')  # Jeden użytkownik może ocenić auto tylko raz
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} → {self.car} = {self.rating}/5"
