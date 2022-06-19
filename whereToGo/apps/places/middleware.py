from string import ascii_letters, digits
import numpy as np
from scipy.spatial.distance import cosine
from . import models
from django.db.models import Sum, Count, ObjectDoesNotExist
from django.db import connection


def string_checking(string):
    for char in string:
        if char not in ascii_letters and char not in digits:
            return False
    return True


def vec_distance(vec_1, vec_2):
    not_none_indexes = []
    for i, feature in np.ndenumerate(vec_1):
        if not np.isnan(feature) and not np.isnan(vec_2[i[0]]):
            not_none_indexes.append(i[0])
    vec_1 = vec_1[not_none_indexes]
    vec_2 = vec_2[not_none_indexes]
    return cosine(vec_1, vec_2) if vec_1.shape[0] > 1 else 1


def get_place_vector(place_id):
    result = models.UsersScores.objects.filter(place_id=place_id).values('place_id')\
        .annotate(score_count=Count('score'), score_sum=Sum('score'))
    if result.exists():
        users_count = result[0]['score_count']
        users_sum = result[0]['score_sum']
    else:
        users_count = 0
        users_sum = 0

    place_info = models.Places.objects.get(place_id=place_id)

    mark_sum = place_info.mark_sum if place_info.mark_sum is not None else 0
    mark_count = place_info.mark_count if place_info.mark_count is not None else 0
    mark_count += users_count
    if mark_count == 0:
        avg_mark = None
    else:
        avg_mark = (users_sum + mark_sum) / mark_count

    try:
        distance = models.Metro.objects.get(place_id=place_id).distance
    except ObjectDoesNotExist:
        distance = None

    info = np.array([avg_mark, place_info.square, distance], dtype=float)

    regions_list = np.zeros(models.RegionsDescription.objects.count(), dtype=float)
    for line in models.Regions.objects.filter(place_id=place_id):
        regions_list[line.region_id - 1] = 100

    category_list = np.zeros(models.CategoriesDescription.objects.count(), dtype=float)
    for line in models.Categories.objects.filter(place_id=place_id):
        category_list[line.category_id - 1] = 100

    return np.concatenate((info, regions_list, category_list))


def finding_similar_places(place_vector, visited_places, scores_info=None, res_count=10):
    places_count = models.Places.objects.count()
    info = np.empty((places_count, 3), dtype=float)
    if scores_info is None:
        scores_info = {}
        result = models.UsersScores.objects.values('place_id').annotate(score_count=Count('score'),
                                                                        score_sum=Sum('score'))
        for _ in result:
            scores_info[_['place_id']] = {'count': _['score_count'], 'sum': _['score_sum']}

    for place in models.Places.objects.all():
        total_sum = place.mark_sum if place.mark_sum is not None else 0
        total_count = place.mark_count if place.mark_count is not None else 0
        if place.place_id in scores_info.keys():
            total_count += scores_info[place.place_id]['count']
            total_sum += scores_info[place.place_id]['sum']
        if total_count == 0:
            avg_mark = None
        else:
            avg_mark = total_sum / total_count

        try:
            metro_query = models.Metro.objects.get(place_id=place.place_id)
            distance = metro_query.distance
        except ObjectDoesNotExist:
            distance = None
        info[place.place_id - 1] = [avg_mark, place.square, distance]

    region_list = np.zeros((places_count, models.RegionsDescription.objects.count()), dtype=float)
    for line in models.Regions.objects.all():
        region_list[line.place_id - 1][line.region_id - 1] = 100

    category_list = np.zeros((places_count, models.CategoriesDescription.objects.count()), dtype=float)
    for line in models.Categories.objects.all():
        category_list[line.place_id - 1][line.category_id - 1] = 100

    all_places = np.concatenate((info, region_list, category_list), axis=1)

    distance_rate = []
    for place_id in range(places_count):
        if place_id + 1 in visited_places:
            continue
        distance_rate.append((place_id + 1, vec_distance(place_vector, all_places[place_id])))

    return sorted(distance_rate, key=lambda x: x[1])[:res_count]


def get_history_vector(user_id, scores_info=None):
    if scores_info is None:
        scores_info = {}
        result = models.UsersScores.objects.values('place_id').annotate(score_count=Count('score'),
                                                                        score_sum=Sum('score'))
        for _ in result:
            scores_info[_['place_id']] = {'count': _['score_count'], 'sum': _['score_sum']}

    users_places = models.UsersScores.objects.filter(user_id=user_id)
    users_places_ids = set()
    info = np.zeros((1, 3), dtype=float)
    for line in users_places:
        users_places_ids.add(line.place_id)
        total_sum = line.place.mark_sum if line.place.mark_sum is not None else 0
        total_count = line.place.mark_count if line.place.mark_count is not None else 0
        if line.place.place_id in scores_info.keys():
            total_count += scores_info[line.place.place_id]['count']
            total_sum += scores_info[line.place.place_id]['sum']
        if total_count == 0:
            avg_mark = None
        else:
            avg_mark = total_sum / total_count
        try:
            metro_query = models.Metro.objects.get(place_id=line.place.place_id)
            distance = metro_query.distance
        except ObjectDoesNotExist:
            distance = 0
        square = line.place.square if line.place.square is not None else 0
        info[0] += np.array([avg_mark, square, distance], dtype=float)

    regions_list = np.zeros((1, models.RegionsDescription.objects.count()), dtype=float)
    categories_list = np.zeros((1, models.CategoriesDescription.objects.count()), dtype=float)

    with connection.cursor() as cursor:
        cursor.execute(f'select us.score, r.region_id '
                       f'from "Regions" as r '
                       f'right join (select score, place_id from "Users_scores" where user_id = {user_id}) as us '
                       f'on r.place_id = us.place_id')
        for score, region_id in cursor.fetchall():
            regions_list[0][region_id - 1] += score

        cursor.execute(f'select us.score, c.category_id '
                       f'from "Categories" as c '
                       f'right join (select score, place_id from "Users_scores" where user_id = {user_id}) as us '
                       f'on c.place_id = us.place_id')
        for score, category_id in cursor.fetchall():
            categories_list[0][category_id - 1] += score

    history = np.concatenate((info, regions_list, categories_list), axis=1)

    history /= users_places.count()

    history[0][1] = history[0][1] if history[0][1] != 0 else np.nan
    history[0][2] = history[0][2] if history[0][2] != 0 else np.nan

    return users_places_ids, history[0]


def get_recommendation_by_history(user_id, rec_count=10):
    scores_info = {}
    result = models.UsersScores.objects.values('place_id').annotate(score_count=Count('score'), score_sum=Sum('score'))
    for _ in result:
        scores_info[_['place_id']] = {'count': _['score_count'], 'sum': _['score_sum']}

    user_places, history = get_history_vector(user_id, scores_info)
    return finding_similar_places(history, user_places, scores_info, rec_count)


def get_recommendation_by_similar_users(user_id, rec_count=10, k=5):
    places_count = models.Places.objects.count()

    user_places = models.UsersScores.objects.filter(user_id=user_id)
    user_places_ids = []
    user_places_indexes = []
    user_scores = np.empty((1, user_places.count()), dtype=int)

    for i, line in enumerate(user_places):
        user_places_ids.append(line.place_id)
        user_places_indexes.append(line.place_id - 1)
        user_scores[0][i] = line.score

    potential_marks = np.zeros((1, places_count), dtype=float)
    with connection.cursor() as cursor:
        query = 'select distinct user_id from "Users_scores" ' \
                'where place_id in (' + ', '.join([str(_) for _ in user_places_ids]) + f') and user_id != {user_id}'
        cursor.execute(query)
        potential_similar = tuple(list(map(lambda x: x[0], cursor.fetchall())))
        potential_count = len(potential_similar)

        users_marks = np.full([potential_count, places_count], np.nan)
        query = 'select user_id, place_id, score from "Users_scores"' \
                ' where user_id in (' + ', '.join([str(_) for _ in potential_similar]) + ')'
        cursor.execute(query)
        for user_id, place_id, score in cursor.fetchall():
            users_marks[potential_similar.index(user_id)][place_id - 1] = score

    users_distance = []
    for i in range(potential_count):
        users_distance.append(vec_distance(user_scores[0], users_marks[i][user_places_indexes]))

    if len(users_distance) > k:
        k_nearest = list(map(lambda t: t[0], sorted(list(enumerate(users_distance)), key=lambda x: x[1])[:k]))
        users_marks = users_marks[k_nearest]

        for i in range(users_marks.shape[0]):
            potential_marks += users_marks[i] * (1 - users_distance[k_nearest[i]])

        potential_marks /= k
    else:
        for i in range(users_marks.shape[0]):
            potential_marks += users_marks[i] * (1 - users_distance[i])

        potential_marks /= users_marks.shape[0]

    recommendation_ids = list(
                                filter(lambda x: x[1] > 5 and x[0] not in user_places_ids and not np.isnan(x[1]),
                                       map(lambda t: (t[0][0] + 1, t[1]),
                                           sorted(list(np.ndenumerate(potential_marks[0])),
                                                  key=lambda x: x[1], reverse=True)[:rec_count])
                                       )
    )

    return recommendation_ids


def get_recommendation(user_id):
    content_rec = get_recommendation_by_history(user_id)
    collab_rec = get_recommendation_by_similar_users(user_id)

    try:
        choice_line = models.UsersChoice.objects.get(user_id=user_id)
        if choice_line.collab + choice_line.content >= 10:
            k_collab_max = max(min(int(choice_line.collab / (choice_line.collab + choice_line.content) * 10), 8), 2)
        else:
            k_collab_max = 5
    except ObjectDoesNotExist:
        k_collab_max = 5

    if len(collab_rec) >= k_collab_max:
        k_collab = k_collab_max
    else:
        k_collab = len(collab_rec)

    return collab_rec[:k_collab] + content_rec[:(10 - k_collab)]

