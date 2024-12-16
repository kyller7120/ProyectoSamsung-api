from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include

router = DefaultRouter()
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'players', PlayersViewSet, basename='player-list')
router.register(r'player-info', PlayerViewSet, basename='player-info')
router.register(r'player-history-info', PlayerValueMarketViewSet, basename='player-history-info')

urlpatterns = [
    path('', include(router.urls))
]
