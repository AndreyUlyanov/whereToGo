from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('<int:user>/', views.home, name='home'),
    path('profile/<int:user>/', views.profile, name='profile'),
    path('sign-in/', views.signIn, name='sign-in'),
    path('sign-up/', views.signUp, name='sign-up'),
    path('sign-out/', views.signOut, name='sign-out'),
    path('sign-in/next/', views.singInButtonPressed, name='signInButtonPressed'),
    path('sign-up/next/', views.singUpButtonPressed, name='signUpButtonPressed'),
    path('place/<int:place_id>/<int:user>/', views.place, name='place'),
    path('ratingPlace/<int:place_id>/<int:user>/', views.ratingPlace, name='ratingPlace'),
    path('revaluePlace/<int:place_id>/<int:user>/', views.revaluePlace, name='revaluePlace'),

]
