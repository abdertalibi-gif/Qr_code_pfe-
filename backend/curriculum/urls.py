from django.urls import path

from .views import (
    curriculum_view,
    filiere_detail,
    filiere_list,
    module_list,
    niveau_list,
    semestre_list,
    semestres_par_niveau,
)

urlpatterns = [
    path("curriculum/", curriculum_view, name="curriculum"),
    path("curriculum/semestres/", semestre_list, name="curriculum-semestres"),
    path("curriculum/semestres-par-niveau/", semestres_par_niveau, name="curriculum-semestres-niveau"),
    path("curriculum/filieres/", filiere_list, name="curriculum-filieres"),
    path("curriculum/filieres/<int:pk>/", filiere_detail, name="curriculum-filiere-detail"),
    path("curriculum/modules/", module_list, name="curriculum-modules"),
    path("curriculum/niveaux/", niveau_list, name="curriculum-niveaux"),
]
