from django.db import models

# Create your models here.


class Places(models.Model):
    place_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True, null=True)
    mark_count = models.IntegerField(blank=True, null=True)
    mark_sum = models.IntegerField(blank=True, null=True)
    square = models.FloatField(blank=True, null=True)
    link = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'Places'


class CategoriesDescription(models.Model):
    category_id = models.AutoField(primary_key=True)
    category = models.CharField(max_length=255)

    class Meta:
        db_table = 'Categories_description'


class Categories(models.Model):
    place = models.ForeignKey('Places', models.CASCADE, blank=True, null=True)
    category = models.ForeignKey('CategoriesDescription', models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'Categories'


class MetroDescription(models.Model):
    metro_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'Metro_description'


class Metro(models.Model):
    place = models.ForeignKey('Places', models.CASCADE, blank=True, null=True)
    metro = models.ForeignKey('MetroDescription', models.CASCADE, blank=True, null=True)
    distance = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'Metro'


class RegionsDescription(models.Model):
    region_id = models.AutoField(primary_key=True)
    region = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'Regions_description'

    def __str__(self):
        return self.region


class Regions(models.Model):
    place = models.ForeignKey(Places, models.CASCADE, blank=True, null=True)
    region = models.ForeignKey('RegionsDescription', models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'Regions'


class Users(models.Model):
    user_id = models.AutoField(primary_key=True)
    login = models.CharField(unique=True, max_length=255)
    password = models.CharField(max_length=255)
    sex = models.BooleanField(blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'Users'


class UsersChoice(models.Model):
    user = models.ForeignKey(Users, models.CASCADE, blank=True, null=True)
    content = models.IntegerField()
    collab = models.IntegerField()

    class Meta:
        db_table = 'Users_choice'


class UsersScores(models.Model):
    # id = models.BigAutoField(primary_key=True, editable=False)
    user = models.ForeignKey(Users, models.CASCADE, blank=True, null=True)
    place = models.ForeignKey(Places, models.CASCADE, blank=True, null=True)
    score = models.IntegerField(blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'Users_scores'
