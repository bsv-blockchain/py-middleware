"""Test URL configuration."""

from django.http import JsonResponse
from django.urls import path


def test_view(request):
    """Simple test view."""
    return JsonResponse({"message": "test"})


def premium_endpoint(request):
    """Premium endpoint for testing - requires payment."""
    return JsonResponse(
        {
            "message": "Premium content accessed",
            "status": "success",
            "premium_data": {"content": "This is premium content", "quality": "high"},
        }
    )


def decorator_payment_endpoint(request):
    """Payment endpoint for testing."""
    return JsonResponse({"message": "Payment endpoint accessed", "status": "success"})


urlpatterns = [
    path("test/", test_view, name="test"),
    path("premium/", premium_endpoint, name="premium"),
    path("decorator-payment/", decorator_payment_endpoint, name="decorator_payment"),
]
