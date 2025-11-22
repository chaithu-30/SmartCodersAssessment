from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health'),
    path('search/', views.search_view, name='search'),
    path('fetch/', views.fetch_url_view, name='fetch_url'),
]

