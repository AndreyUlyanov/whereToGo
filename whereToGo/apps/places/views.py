from django.core.paginator import Paginator
from django.shortcuts import render
from .models import *
from .middleware import *
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from django.http import Http404
from uuid import uuid4
from hashlib import sha256

# Create your views here.


def home(request, user=0):
    return render(request, 'places/home.html', {'user': user})


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
    if date:
        try:
            year, month, day = list(map(int, date.split('-')))
            birthday = f"{year}-{month:02}-{day:02}"
            trial = datetime(year, month, day)
        except ValueError:
            return signUp(request, 'Неверная дата')
    else:
        birthday = None

    checking = string_checking(login) and string_checking(password) and string_checking(password_again)
    if not checking:
        return signUp(request, "Поля должны содержать латинские буквы или числа.")
    if len(password) <= 7:
        return signUp(request, "Пароль должен содержать не менее 8 символов.")
    if password != password_again:
        return signUp(request, "Пароли не совпадают.")

    salt = uuid4().hex
    password = (sha256(salt.encode() + password.encode()).hexdigest()) + ':' + salt
    try:
        login_not_taken = False
        Users.objects.get(login=login)
    except ObjectDoesNotExist:
        login_not_taken = True

    if not login_not_taken:
        return signUp(request, 'Такой логин уже используется, введите другой.')

    user_id = Users.objects.count() + 1
    user = Users.objects.create(user_id=user_id, login=login, password=password, sex=sex, birthday=birthday)
    user.save()
    return home(request, user_id)


def singInButtonPressed(request):
    login = request.POST['login']
    password = request.POST['password']
    checking = string_checking(login) and string_checking(password)
    if not checking:
        return signIn(request, "Логин и пароль должны использовать только латинские буквы и цифры.")
    try:
        user = Users.objects.get(login=login)
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
    space = Places.objects.get(place_id=place_id)
    if space is None:
        Http404()
    else:
        similar_places = finding_similar_places(get_place_vector(place_id), [place_id])

        scores = models.UsersScores.objects.filter(place_id=space.place_id).values('place_id') \
            .annotate(score_count=Count('score'), score_sum=Sum('score'))
        if scores.exists():
            users_count = scores[0]['score_count']
            users_sum = scores[0]['score_sum']
        else:
            users_count = 0
            users_sum = 0
        mark_sum = space.mark_sum if space.mark_sum is not None else 0
        mark_count = space.mark_count if space.mark_count is not None else 0
        mark_count += users_count
        if mark_count == 0:
            avg_mark = None
        else:
            avg_mark = round((users_sum + mark_sum) / mark_count, 2)

        category_list = Categories.objects.filter(place_id=space.place_id)
        region_list = Regions.objects.filter(place_id=space.place_id)
        try:
            user_score = UsersScores.objects.get(place_id=space.place_id, user_id=user)
        except ObjectDoesNotExist:
            user_score = None
        score_command = 'revaluePlace' if user_score is not None else 'ratingPlace'

        return render(request, 'places/place.html',
                      {'user': user, 'place': space, 'avg_mark': avg_mark, 'category_list': category_list,
                       'region_list': region_list, 'user_score': user_score, 'score_command': score_command,
                       'message': message, 'similar_places': similar_places})

    return render(request, 'places/place.html', {'place_id': place_id, 'user': user, 'message': message})


def ratingPlace(request, place_id, user):
    try:
        score = int(request.POST['score'])
    except ValueError:
        message = 'Оценка должна быть числом.'
        return place(request, place_id, user, message)

    if score <= 0 or score > 10:
        message = 'Оценка должна быть числом от 0 до 10.'
        return place(request, place_id, user, message)

    birthday = Users.objects.get(user_id=user).birthday
    if birthday is None:
        rating = UsersScores(user_id=user, place_id=place_id, score=score)
    else:
        age = (datetime.now() - datetime(birthday.year, birthday.month, birthday.day)).days // 365
        rating = UsersScores(user_id=user, place_id=place_id, score=score, age=age)
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

    birthday = Users.objects.get(user_id=user).birthday
    if birthday is None:
        age = None
    else:
        age = (datetime.now() - datetime(birthday.year, birthday.month, birthday.day)).days // 365

    try:
        data = UsersScores.objects.get(place_id=place_id, user_id=user)
        data.score = score
        if age is not None:
            data.age = age
        data.save()
        return place(request, place_id, user)
    except:
        message = 'Что-то пошло не так. Попробуйте ещё раз.'
        return place(request, place_id, user, message)


def profile(request, user):
    user_info = Users.objects.get(user_id=user)
    recommendations = get_recommendation(user)

    all_user_marks = UsersScores.objects.filter(user_id=user).values('place_id', 'score')

    paginator = Paginator(all_user_marks, 10)
    page_number = request.GET.get('page')
    user_marks = paginator.get_page(page_number)

    return render(request, 'places/profile.html', {'user': user, 'user_info': user_info, 'user_marks': user_marks,
                                                   'recommendations': recommendations})


def all_places(request, user, message=''):
    categories = CategoriesDescription.objects.all()
    regions = RegionsDescription.objects.all()
    metro = MetroDescription.objects.all()
    return render(request, 'places/places.html', {'user': user, 'message': message, 'categories': categories,
                                                  'regions': regions, 'metro': metro})


def search_results(request, user):
    target = request.POST['search']
    message = ''
    for i in target:
        if i.lower() not in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' and i not in ascii_letters \
                and i not in digits and i != ' ':
            message = 'В поисковой строке могут находится буквы латинского и кириллического алфавитов, ' \
                      'а также цифры и пробел.'
            break

    if len(message) > 0:
        return all_places(request, user, message)

    finding_places = Places.objects.filter(name__contains=target)

    if len(finding_places) == 0:
        message = 'По данному запросу ничего не найдено.'
        return all_places(request, user, message)

    return render(request, 'places/searchResults.html', {'user': user, 'results': finding_places[:50]})


def filter_places(request, user):
    if 'query' in request.POST.keys():
        query = request.POST['query']
    else:
        subquery = ''
        categories = request.POST.getlist('category')
        if len(categories) != 0:
            categories_list = '(' + ', '.join([f"'{_}'" for _ in categories]) + ')'
            subquery += f"""
                            select place_id from "Categories"
                            where category_id in (select category_id from "Categories_description"
                                                    where category in {categories_list})
                        """

        regions = request.POST.getlist('region')
        if len(regions) != 0:
            regions_list = '(' + ', '.join([f"'{_}'" for _ in regions]) + ')'
            if subquery:
                subquery += f"""
                                union all
                                select place_id from "Regions"
                                where region_id in (select region_id from "Regions_description"
                                                    where region in {regions_list})
                            """
            else:
                subquery += f"""
                                select place_id from "Regions"
                                where region_id in (select region_id from "Regions_description"
                                                    where region in {regions_list})
                            """

        metro = request.POST.getlist('metro')
        if len(metro) != 0:
            metro_list = '(' + ', '.join([f"'{_}'" for _ in metro]) + ')'
            if subquery:
                subquery += f"""
                                union all
                                select place_id from "Metro"
                                where metro_id in (select metro_id from "Metro_description"
                                                    where name in {metro_list})
                            """
            else:
                subquery += f"""
                                select place_id from "Metro"
                                where metro_id in (select metro_id from "Metro_description"
                                                    where name in {metro_list})
                            """

        if subquery:
            query = f"""
                        select distinct filter.place_id, p.name
                        from ({subquery}) as filter
                        left join "Places" as p
                        on p.place_id = filter.place_id 
                    """
        else:
            query = """
                        select distinct place_id, name
                        from "Places"    
                    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        results = list(map(lambda x: {'place_id': x[0], 'name': x[1]}, cursor.fetchall()))

    paginator = Paginator(results, 10)
    page_number = request.GET.get('page')
    filtered_places = paginator.get_page(page_number)

    return render(request, 'places/searchResults.html', {'user': user, 'results': filtered_places,
                                                         'query': query})


def compilations(request, user):
    scores_info = {}
    result = models.UsersScores.objects.values('place_id').annotate(score_count=Count('score'),
                                                                    score_sum=Sum('score'))
    for _ in result:
        scores_info[_['place_id']] = {'count': _['score_count'], 'sum': _['score_sum']}

    popular_places = {}
    for line in Places.objects.all():
        total_sum = line.mark_sum if line.mark_sum is not None else 0
        total_count = line.mark_count if line.mark_count is not None else 0
        if line.place_id in scores_info.keys():
            total_count += scores_info[line.place_id]['count']
            total_sum += scores_info[line.place_id]['sum']
        if total_count <= 10:
            avg_mark = None
        else:
            avg_mark = total_sum / total_count

        popular_places[line] = avg_mark
    top_10_places = list(map(lambda x: x[0],
                             sorted(
                                 filter(lambda x: x[1] is not None, popular_places.items()),
                                 key=lambda x: x[1], reverse=True)
                             ))[:10]

    places_in_center = Places.objects.filter(regions__region__region_id=1).order_by('mark_count')[:10]
    places_near_begovaya = Places.objects.filter(metro__metro__metro_id=12)[:10]
    collections = {'Топ-10 мест по средней оценке': top_10_places,
                   'Популярные места центрального района': places_in_center,
                   'Рядом со станцией Беговая': places_near_begovaya}

    return render(request, 'places/compilation.html', {'user': user, 'collections': collections})

