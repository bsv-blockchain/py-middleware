"""
URL configuration for BSV middleware example app.
"""

from django.urls import path
from . import views

urlpatterns = [
    # BSV Authentication endpoint
    path('.well-known/bsv/auth', views.bsv_auth_wellknown, name='bsv_auth'),
    # Compatibility alias for clients expecting /.well-known/auth
    path('.well-known/auth', views.bsv_auth_wellknown, name='bsv_auth_compat'),
    
    # Simple test endpoint
    path('test/', views.simple_test, name='simple_test'),
    
    # Free endpoints
    path('', views.home, name='home'),
    path('health/', views.health, name='health'),
    path('public/', views.public_endpoint, name='public'),
    
    # Protected endpoints
    path('protected/', views.protected_endpoint, name='protected'),
    path('premium/', views.premium_endpoint, name='premium'),
    
    # Test endpoints
    path('auth-test/', views.auth_test, name='auth_test'),
    path('decorator-auth/', views.decorator_auth_example, name='decorator_auth'),
    path('decorator-payment/', views.decorator_payment_example, name='decorator_payment'),
    path('hello-bsv/', views.hello_bsv_endpoint, name='hello_bsv'),  # 認証 + 支払い → "Hello BSV"
]
