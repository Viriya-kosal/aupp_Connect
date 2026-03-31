from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


DEPARTMENT_CHOICES = [
    ('CS',    'Computer Science'),
    ('BBA',   'Business Administration'),
    ('ENG',   'Engineering'),
    ('LAW',   'Law'),
    ('ART',   'Arts & Humanities'),
    ('SCI',   'Natural Sciences'),
    ('OTHER', 'Other'),
]

COURSE_TAG_CHOICES = [
    ('',        '— No tag —'),
    ('COSC221', 'COSC 221 - Advanced Python'),
    ('COSC101', 'COSC 101 - Intro to CS'),
    ('COSC310', 'COSC 310 - Data Structures'),
    ('COSC350', 'COSC 350 - Machine Learning'),
    ('BBA301',  'BBA 301 - Economics'),
    ('BBA210',  'BBA 210 - Marketing'),
    ('ENG201',  'ENG 201 - Calculus'),
    ('GENERAL', 'General / Campus Life'),
]


class StudentManager(BaseUserManager):
    def create_user(self, email, username, first_name, last_name, password=None, **extra):
        if not email:
            raise ValueError('Email required')
        email = self.normalize_email(email)
        initials = (first_name[0] + last_name[0]).upper() if first_name and last_name else email[:2].upper()
        user = self.model(email=email, username=username,
                          first_name=first_name, last_name=last_name,
                          avatar_initials=initials, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user


class Student(AbstractBaseUser):
    email           = models.EmailField(unique=True)
    username        = models.CharField(max_length=64, unique=True)
    first_name      = models.CharField(max_length=64)
    last_name       = models.CharField(max_length=64)
    department      = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES, default='CS')
    year_level      = models.IntegerField(default=1)
    bio             = models.TextField(blank=True, default='')
    avatar_initials = models.CharField(max_length=4, blank=True, default='')
    created_at      = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)
    is_staff  = models.BooleanField(default=False)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    objects = StudentManager()

    def __str__(self):
        return self.email


class Post(models.Model):
    author     = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='posts')
    body       = models.TextField()
    image_path = models.CharField(max_length=500, blank=True, default='')
    course_tag = models.CharField(max_length=20, blank=True, default='')
    sentiment  = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Post #{self.pk} by {self.author.username}'


class Comment(models.Model):
    post       = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author     = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='comments')
    body       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class Like(models.Model):
    post       = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user       = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')

class Bookmark(models.Model):
    post       = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='bookmarks')
    user       = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        unique_together = ('post', 'user')   # one bookmark per user per post
        ordering        = ['-created_at']
 
    def __str__(self):
        return f'{self.user} bookmarked {self.post_id}'
 
 
class Share(models.Model):
    post       = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='shares')
    user       = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='shares')
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-created_at']
 
    def __str__(self):
        return f'{self.user} shared {self.post_id}'