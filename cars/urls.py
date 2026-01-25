from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('download/', views.download_csv, name='download_csv'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path("recommend/", views.recommend_car, name="recommend_car"),
    path('search/', views.search, name='search'),
    path('get-models/', views.get_models_by_brand, name='get_models_by_brand'),
    path("get-engines/", views.get_engines, name="get_engines"),
    path('quiz/', views.quiz_view, name='quiz'),
    path('quiz/results/', views.quiz_results_view, name='quiz_results'),


]
