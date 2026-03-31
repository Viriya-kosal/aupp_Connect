from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/',          views.register,        name='register'),
    path('login/',             views.login,            name='login'),

    # Posts
    path('posts/',             views.posts,            name='posts'),
    path('posts/<int:post_id>/',         views.post_detail,    name='post_detail'),      # PATCH / DELETE
    path('posts/<int:post_id>/like/',    views.toggle_like,    name='toggle_like'),
    path('posts/<int:post_id>/comments/',views.comments,       name='comments'),
    path('posts/<int:post_id>/bookmark/',views.toggle_bookmark,name='toggle_bookmark'),
    path('posts/<int:post_id>/share/',   views.share_post,     name='share_post'),

    # Comments
    path('comments/<int:comment_id>/',  views.comment_detail,  name='comment_detail'),  # DELETE

    # Bookmarks list
    path('bookmarks/',         views.bookmarks_list,  name='bookmarks_list'),

    # Stats / discovery
    path('trending/',          views.trending_tags,   name='trending_tags'),
    path('sentiment-today/',   views.sentiment_today, name='sentiment_today'),
    path('stats/',             views.stats_summary,   name='stats_summary'),
    path('metadata/',          views.metadata,        name='metadata'),
]