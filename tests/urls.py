"""Test URL configuration."""

from django.urls import path
from django.http import JsonResponse

def test_view(request):
    """Simple test view."""
    return JsonResponse({'message': 'test'})

urlpatterns = [
    path('test/', test_view, name='test'),
]
