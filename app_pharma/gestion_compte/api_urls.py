from rest_framework.routers import DefaultRouter
from .api_views import UtilisateurViewSet, PharmacieViewSet

router = DefaultRouter()
router.register('utilisateurs', UtilisateurViewSet)
router.register('pharmacies', PharmacieViewSet)

urlpatterns = router.urls