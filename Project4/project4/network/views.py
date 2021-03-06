from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from .models import User, Post, Follow

def index(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            current_user = request.user
            new_post_text = request.POST["new_post_text"]
            Post.objects.create(poster = current_user, post = new_post_text)
    posts = Post.objects.all().order_by("-timestamp")
    partial_posts = pagination(request, posts)
    return render(request, "network/index.html", {
        "posts": partial_posts
    })

@login_required
@csrf_exempt
def edit_post(request, post_id):
    post = Post.objects.get(id = post_id)
    if request.user != post.poster:
        return JsonResponse({"error": "Editing restricted to poster"}, status = 400)
    if request.method != "PUT":
        return JsonResponse({"error": "PUT request required"}, status = 400)
    json_data = json.loads(request.body)
    post_data = json_data.get("edited_post_text", "")
    post.post = post_data
    post.save()
    return JsonResponse({"message": "Post Edited"}, status = 201)

@login_required
@csrf_exempt
def like_post(request, post_id):
    if request.method != "PUT":
        return JsonResponse({"error": "PUT request required"}, status = 400)
    post = Post.objects.get(id = post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    post.save()
    return JsonResponse({"message": "Post Edited", "likes_num": str(post.likes.count())}, status = 201)

@login_required
@csrf_exempt
def delete_post(request, post_id):
    post = Post.objects.get(id = post_id)
    if request.user != post.poster:
        return JsonResponse({"error": "Deletion restricted to poster"}, status = 400)
    if request.method != "PUT":
        return JsonResponse({"error": "PUT request required"}, status = 400)
    post.delete()
    return JsonResponse({"message": "Post Deleted"}, status = 201)

def user_page(request, user_id):
    requested_user = User.objects.get(id = user_id)
    posts = Post.objects.filter(poster = requested_user).order_by("-timestamp")
    partial_posts = pagination(request, posts)

    follow_status = False
    if request.user.is_authenticated:
        if request.method == "POST" and request.user != requested_user:
            if request.user.followsbyuser.filter(following = requested_user).exists():
                request.user.followsbyuser.filter(following = requested_user).delete()
            else:
                Follow(follower = request.user, following = requested_user).save()
        if request.user.followsbyuser.filter(following = requested_user).exists():
            follow_status = True

    return render(request, "network/user_page.html", {
        "requested_user": requested_user,
        "posts": partial_posts,
        "followers": len(requested_user.followsonuser.all()),
        "following": len(requested_user.followsbyuser.all()),
        "follow_status": follow_status
    })

@login_required
def following_page(request):
    followed_users = [follow.following for follow in request.user.followsbyuser.all()]
    posts = Post.objects.filter(poster__in = followed_users).order_by("-timestamp")
    partial_posts = pagination(request, posts)
    return render(request, "network/following_page.html", {
        "posts": partial_posts
    })

def pagination(request, posts):
    page = request.GET.get('page', 1)
    paginator = Paginator(posts, 10)
    try:
        partial_posts = paginator.page(page)
    except PageNotAnInteger:
        partial_posts = paginator.page(1)
    except EmptyPage:
        partial_posts = paginator.page(paginator.num_pages)
    return partial_posts


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "network/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "network/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "network/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "network/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "network/register.html")
