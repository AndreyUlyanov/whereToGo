from django.shortcuts import render
from . import models
from .middleware import string_checking
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from django.http import Http404
from uuid import uuid4
from hashlib import sha256

# Create your views here.


def home(request, user=0):
    content = models.Places.objects.get(place_id=1)
    return render(request, 'places/home.html', {'user': user, 'content': content.name})


def signOut(request):
    return render(request, 'places/home.html', {'user': 0})


def signUp(request, message=''):
    return render(request, 'places/signUp.html', {'user': 0, 'message': message})


def singUpButtonPressed(request):
    login = request.POST['login']
    password = request.POST['password']
    password_again = request.POST['password_again']
    sex = request.POST.get('M', False)
    date = request.POST['date']

    try:
        year, month, day = list(map(int, date.split('-')))
        birthday = f"{year}-{month:02}-{day:02}"
        trial = datetime(year, month, day)
    except ValueError:
        return signUp(request, 'Неверная дата')

    checking = string_checking(login) and string_checking(password) and string_checking(password_again)
    if not checking:
        return signUp(request, "Поля должны содержать латинские буквы или числа.")
    if password != password_again:
        return signUp(request, "Пароли не совпадают.")

    salt = uuid4().hex
    password = (sha256(salt.encode() + password.encode()).hexdigest()) + ':' + salt
    try:
        login_not_taken = False
        models.Users.objects.get(login=login)
    except ObjectDoesNotExist:
        login_not_taken = True

    if not login_not_taken:
        return signUp(request, 'Такой логин уже используется, введите другой.')

    user_id = models.Users.objects.count() + 1
    user = models.Users.objects.create(user_id=user_id, login=login, password=password, sex=sex, birthday=birthday)
    user.save()
    return home(request, user_id)


def singInButtonPressed(request):
    login = request.POST['login']
    password = request.POST['password']
    checking = string_checking(login) and string_checking(password)
    if not checking:
        return signIn(request, "Логин и пароль должны использовать только латинские буквы и цифры.")
    try:
        user = models.Users.objects.get(login=login)
        encrypted_pass, salt = user.password.split(':')
        if encrypted_pass == (sha256(salt.encode() + password.encode()).hexdigest()):
            return home(request, user.user_id)
        else:
            return signIn(request, 'Неверный пароль.')
    except ObjectDoesNotExist:
        return signIn(request, "Такого логина не существует. Попробуйте снова.")


def signIn(request, message=''):
    return render(request, 'places/signIn.html', {'user': 0, 'message': message})


def place(request, place_id, user=0, message=''):
    space = models.Places.objects.get(place_id=place_id)
    if space is None:
        Http404()
    else:
        try:
            scores = models.UsersScores.objects.get(place_id=space.place_id)
        except ObjectDoesNotExist:
            scores = None
        category_list = models.Categories.objects.filter(place_id=space.place_id)
        region_list = models.Regions.objects.filter(place_id=space.place_id)
        try:
            user_score = models.UsersScores.objects.get(place_id=space.place_id, user_id=user)
        except ObjectDoesNotExist:
            user_score = None
        score_command = 'revaluePlace' if user_score is not None else 'ratingPlace'

        return render(request, 'places/place.html',
                      {'user': user, 'place': space, 'scores': scores, 'category_list': category_list,
                       'region_list': region_list, 'user_score': user_score, 'score_command': score_command,
                       'message': message})

    return render(request, 'places/place.html', {'place_id': place_id, 'user': user, 'message': message})


def ratingPlace(request, place_id, user):
    try:
        score = int(request.POST['score'])
    except ValueError:
        message = 'Оценка должна быть числом.'
        return place(request, place_id, user, message)

    if score < 0 or score > 10:
        message = 'Оценка должна быть числом от 0 до 10.'
        return place(request, place_id, user, message)

    birthday = models.Users.objects.get(user_id=user).birthday
    if birthday is None:
        rating = models.UsersScores(user_id=user, place_id=place_id, score=score)
    else:
        age = (datetime.now() - datetime(birthday.year, birthday.month, birthday.day)).days // 365
        rating = models.UsersScores(user_id=user, place_id=place_id, score=score, age=age)
    try:
        rating.save()
        return place(request, place_id, user)
    except:
        message = 'Что-то пошло не так. Попробуйте ещё раз.'
        return place(request, place_id, user, message)


def revaluePlace(request, place_id, user):
    score = 7
    try:
        score = int(request.POST['score'])
    except ValueError:
        message = 'Оценка должна быть целым числом.'
        place(request, place_id, user, message)

    if score < 0 or score > 10:
        message = 'Пожалуйста введите оценку от 0 до 10.'
        return place(request, place_id, user, message)
    try:
        data = models.UsersScores.objects.get(place_id=place_id, user_id=user)
        data.score = score
        data.save()
        return place(request, place_id, user)
    except:
        message = 'Что-то пошло не так. Попробуйте ещё раз.'
        return place(request, place_id, user, message)


def profile(request, user=0):
    pass
