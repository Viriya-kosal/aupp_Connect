import json
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import IntegrityError
from django.db.models import Count

from .models import Student, Post, Comment, Like, Bookmark, Share, DEPARTMENT_CHOICES, COURSE_TAG_CHOICES


def _student_to_dict(s):
    return {
        'id':              s.id,
        'email':           s.email,
        'username':        s.username,
        'first_name':      s.first_name,
        'last_name':       s.last_name,
        'department':      s.department,
        'year_level':      s.year_level,
        'bio':             s.bio,
        'avatar_initials': s.avatar_initials,
    }


def _post_to_dict(p, current_user_id=None):
    return {
        'id':                p.id,
        'body':              p.body,
        'image_path':        p.image_path,
        'course_tag':        p.course_tag,
        'sentiment':         p.sentiment,
        'created_at':        p.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'author_id':         p.author_id,
        'first_name':        p.author.first_name,
        'last_name':         p.author.last_name,
        'avatar_initials':   p.author.avatar_initials,
        'department':        p.author.department,
        'year_level':        p.author.year_level,
        'like_count':        p.likes.count(),
        'comment_count':     p.comments.count(),
        'share_count':       p.shares.count(),
        'liked_by_me':       (
            p.likes.filter(user_id=current_user_id).exists()
            if current_user_id else False
        ),
        'bookmarked_by_me':  (
            p.bookmarks.filter(user_id=current_user_id).exists()
            if current_user_id else False
        ),
    }


def _comment_to_dict(c):
    return {
        'id':              c.id,
        'post_id':         c.post_id,
        'body':            c.body,
        'created_at':      c.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'author_id':       c.author_id,
        'first_name':      c.author.first_name,
        'last_name':       c.author.last_name,
        'avatar_initials': c.author.avatar_initials,
    }


# ── Auth ──────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def register(request):
    data = json.loads(request.body)
    required = ['email', 'username', 'first_name', 'last_name', 'password']
    if not all(data.get(k) for k in required):
        return JsonResponse({'ok': False, 'error': 'All fields are required.'}, status=400)
    if len(data['password']) < 6:
        return JsonResponse({'ok': False, 'error': 'Password must be at least 6 characters.'}, status=400)
    try:
        student = Student.objects.create_user(
            email=data['email'],
            username=data['username'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            password=data['password'],
            department=data.get('department', 'CS'),
            year_level=int(data.get('year_level', 1)),
        )
        return JsonResponse({'ok': True, 'user': _student_to_dict(student)})
    except IntegrityError as e:
        msg = 'Email already registered.' if 'email' in str(e) else 'Username already taken.'
        return JsonResponse({'ok': False, 'error': msg}, status=400)


@csrf_exempt
@require_http_methods(['POST'])
def login(request):
    data     = json.loads(request.body)
    email    = data.get('email', '').strip()
    password = data.get('password', '')
    try:
        student = Student.objects.get(email=email)
        if student.check_password(password):
            return JsonResponse({'ok': True, 'user': _student_to_dict(student)})
    except Student.DoesNotExist:
        pass
    return JsonResponse({'ok': False, 'error': 'Invalid email or password.'}, status=401)


# ── Posts ─────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def posts(request):
    if request.method == 'GET':
        current_user_id = request.GET.get('user_id')
        qs = Post.objects.select_related('author').all()
        return JsonResponse({'posts': [_post_to_dict(p, current_user_id) for p in qs]})

    data = json.loads(request.body)
    try:
        author = Student.objects.get(id=data['author_id'])
    except Student.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'User not found.'}, status=404)

    sentiment = ''
    try:
        from .sentiment import get_sentiment
        sentiment = get_sentiment(data.get('body', ''))
    except Exception:
        pass

    post = Post.objects.create(
        author=author,
        body=data.get('body', ''),
        course_tag=data.get('course_tag', ''),
        sentiment=sentiment,
        image_path=data.get('image_path', ''),
    )
    return JsonResponse({'ok': True, 'post': _post_to_dict(post, author.id)})


@csrf_exempt
@require_http_methods(['PATCH', 'DELETE'])
def post_detail(request, post_id):
    """Edit or delete a single post (owner only)."""
    try:
        post = Post.objects.select_related('author').get(id=post_id)
    except Post.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Post not found.'}, status=404)

    data    = json.loads(request.body) if request.body else {}
    user_id = data.get('user_id') or request.GET.get('user_id')

    if str(post.author_id) != str(user_id):
        return JsonResponse({'ok': False, 'error': 'Permission denied.'}, status=403)

    if request.method == 'DELETE':
        post.delete()
        return JsonResponse({'ok': True})

    # PATCH — edit body
    new_body = data.get('body', '').strip()
    if not new_body:
        return JsonResponse({'ok': False, 'error': 'Body cannot be empty.'}, status=400)
    post.body = new_body

    # Re-run sentiment if available
    try:
        from .sentiment import get_sentiment
        post.sentiment = get_sentiment(new_body)
    except Exception:
        pass

    post.save()
    return JsonResponse({'ok': True, 'post': _post_to_dict(post, user_id)})


# ── Comments ──────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def comments(request, post_id):
    if request.method == 'GET':
        qs = Comment.objects.select_related('author').filter(post_id=post_id)
        return JsonResponse({'comments': [_comment_to_dict(c) for c in qs]})

    data = json.loads(request.body)
    try:
        post   = Post.objects.get(id=post_id)
        author = Student.objects.get(id=data['author_id'])
    except (Post.DoesNotExist, Student.DoesNotExist) as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=404)

    comment = Comment.objects.create(post=post, author=author, body=data.get('body', ''))
    return JsonResponse({'ok': True, 'comment': _comment_to_dict(comment)})


@csrf_exempt
@require_http_methods(['DELETE'])
def comment_detail(request, comment_id):
    """Delete a single comment (owner only)."""
    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Comment not found.'}, status=404)

    data    = json.loads(request.body) if request.body else {}
    user_id = data.get('user_id') or request.GET.get('user_id')

    if str(comment.author_id) != str(user_id):
        return JsonResponse({'ok': False, 'error': 'Permission denied.'}, status=403)

    comment.delete()
    return JsonResponse({'ok': True})


# ── Likes ─────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def toggle_like(request, post_id):
    data = json.loads(request.body)
    try:
        post = Post.objects.get(id=post_id)
        user = Student.objects.get(id=data['user_id'])
    except (Post.DoesNotExist, Student.DoesNotExist) as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=404)

    like, created = Like.objects.get_or_create(post=post, user=user)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    return JsonResponse({'ok': True, 'liked': liked, 'like_count': post.likes.count()})


# ── Bookmarks ─────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def toggle_bookmark(request, post_id):
    data = json.loads(request.body)
    try:
        post = Post.objects.get(id=post_id)
        user = Student.objects.get(id=data['user_id'])
    except (Post.DoesNotExist, Student.DoesNotExist) as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=404)

    bm, created = Bookmark.objects.get_or_create(post=post, user=user)
    if not created:
        bm.delete()
        bookmarked = False
    else:
        bookmarked = True

    return JsonResponse({'ok': True, 'bookmarked': bookmarked})


@require_http_methods(['GET'])
def bookmarks_list(request):
    """Return all bookmarked posts for a user."""
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'user_id required.'}, status=400)
    qs = (Post.objects
          .select_related('author')
          .filter(bookmarks__user_id=user_id)
          .order_by('-bookmarks__created_at'))
    return JsonResponse({'posts': [_post_to_dict(p, user_id) for p in qs]})


# ── Shares ────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def share_post(request, post_id):
    data = json.loads(request.body)
    try:
        post = Post.objects.get(id=post_id)
        user = Student.objects.get(id=data['user_id'])
    except (Post.DoesNotExist, Student.DoesNotExist) as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=404)

    Share.objects.create(post=post, user=user)
    return JsonResponse({'ok': True, 'share_count': post.shares.count()})


# ── Discovery / Stats ─────────────────────────────────────────────────────────

@require_http_methods(['GET'])
def trending_tags(request):
    limit = int(request.GET.get('limit', 5))
    qs = (Post.objects
          .exclude(course_tag='')
          .values('course_tag')
          .annotate(count=Count('id'))
          .order_by('-count')[:limit])
    return JsonResponse({'tags': list(qs)})


@require_http_methods(['GET'])
def sentiment_today(request):
    today = datetime.now().date()
    qs    = Post.objects.filter(created_at__date=today)
    total = qs.count() or 1
    pos   = qs.filter(sentiment='positive').count()
    neu   = qs.filter(sentiment='neutral').count()
    neg   = qs.filter(sentiment='negative').count()
    return JsonResponse({
        'positive': round(pos / total * 100),
        'neutral':  round(neu / total * 100),
        'negative': round(neg / total * 100),
    })


@require_http_methods(['GET'])
def stats_summary(request):
    total_posts  = Post.objects.count()
    active_users = Post.objects.values('author').distinct().count()
    total_shares = Share.objects.count()
    top = (Post.objects.exclude(course_tag='')
           .values('course_tag')
           .annotate(count=Count('id'))
           .order_by('-count')
           .first())
    top_tag   = top['course_tag'] if top else 'N/A'
    seven_ago = datetime.now() - timedelta(days=7)
    daily = (Post.objects
             .filter(created_at__gte=seven_ago)
             .extra(select={'date': "date(created_at)"})
             .values('date')
             .annotate(count=Count('id'))
             .order_by('date'))
    return JsonResponse({
        'total_posts':  total_posts,
        'active_users': active_users,
        'total_shares': total_shares,
        'top_tag':      top_tag,
        'daily_posts':  list(daily),
    })


@require_http_methods(['GET'])
def metadata(request):
    return JsonResponse({
        'departments': dict(DEPARTMENT_CHOICES),
        'course_tags': dict(COURSE_TAG_CHOICES),
    })