from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from ultimatereview.forms import UserForm, UserProfileForm, UpdateProfileForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from models import Review, Researcher, Query, Paper
from django.template.defaultfilters import slugify
import search
import datetime
import json

def index(request):
    return render(request, 'ultimatereview/index.html',{})

@login_required
def myprofile(request):
    user = request.user
    form = UserForm(initial={'username':user.username, 'email':user.email, 'password':user.password})
    if request.method == 'POST':

            user.username = request.POST['username']
            user.email = request.POST['email']
            if request.POST['password'] != "": # Checking for an empty password field.
                user.set_password(request.POST['password']) # If password is not empty, then set a new password.

            user.save() # All changes are saved.

    # Now display the updated form details.
    form = UserForm(initial={'username':user.username, 'email':user.email, 'password':user.password})
    context = {
        "form": form
    }
    return render(request, 'ultimatereview/myprofile.html', context)

def register(request):

    # A boolean value for telling the template whether the registration was successful.
    # Set to False initially. Code changes value to True when registration succeeds.
    registered = False

    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        # If the two forms are valid...
        if user_form.is_valid() and profile_form.is_valid():
            # Save the user's form data to the database.
            user = user_form.save()

            # Now we hash the password with the set_password method.
            # Once hashed, we can update the user object.
            user.set_password(user.password)
            user.save()

            # Now sort out the UserProfile instance.
            # Since we need to set the user attribute ourselves, we set commit=False.
            # This delays saving the model until we're ready to avoid integrity problems.
            profile = profile_form.save(commit=False)
            profile.user = user

            # Did the user provide a profile picture?
            # If so, we need to get it from the input form and put it in the UserProfile model.
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            # Now we save the UserProfile model instance.
            profile.save()

            # Update our variable to tell the template registration was successful.
            registered = True

        # Invalid form or forms - mistakes or something else?
        # Print problems to the terminal.
        # They'll also be shown to the user.
        else:
            print user_form.errors, profile_form.errors

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    # Render the template depending on the context.
    return render(request,
            'ultimatereview/register.html',
            {'user_form': user_form, 'profile_form': profile_form, 'registered': registered} )

def user_login(request):

    # If the request is a HTTP POST, try to pull out the relevant information.
    if request.method == 'POST':
        # Gather the username and password provided by the user.
        # This information is obtained from the login form.
                # We use request.POST.get('<variable>') as opposed to request.POST['<variable>'],
                # because the request.POST.get('<variable>') returns None, if the value does not exist,
                # while the request.POST['<variable>'] will raise key error exception
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Use Django's machinery to attempt to see if the username/password
        # combination is valid - a User object is returned if it is.
        user = authenticate(username=username, password=password)

        # If we have a User object, the details are correct.
        # If None (Python's way of representing the absence of a value), no user
        # with matching credentials was found.
        if user:
            # Is the account active? It could have been disabled.
            if user.is_active:
                # If the account is valid and active, we can log the user in.
                # We'll send the user back to the homepage.
                login(request, user)
                return HttpResponseRedirect('/ultimatereview/')
            else:
                # An inactive account was used - no logging in!
                return HttpResponse("Your Ultimate Review account is disabled.")
        else:
            # Bad login details were provided. So we can't log the user in.
			return render(request, 'ultimatereview/login.html', {'alert_message':"Invalid login details."})
            

    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        # No context variables to pass to the template system, hence the
        # blank dictionary object...
        return render(request, 'ultimatereview/login.html', {})

@login_required
def myreviews(request):
	reviews = Review.objects.filter(user=request.user).order_by('-date_started')
	context = {'reviews':reviews, 'alert_message':None}
	if request.method == "POST":
            new_title=(request.POST.get('review', ""))
            new_title= new_title.strip()
	    if not request.POST.get('review', "")=="":
		if not any(c in '!@#$%^&*\"\'' for c in new_title):
		    if not reviews.filter(slug=slugify(new_title).exists():
			review = Review(user=request.user, title=new_title, date_started=datetime.datetime.now())
			review.save()
			reviews = Review.objects.filter(user=request.user).order_by('-date_started')
			context['reviews']=reviews
		    else:
			context['alert_message']="A review with this name already exists."
                else:
				context['alert_message']="Title cannot contain !@#$%^&*\"\'"
	    elif request.POST.get('delete_review', "")!="":
                review_to_delete=Review.objects.get(slug=request.POST.get('delete_review'))
	if review_to_delete!=None:
	    review_to_delete.delete()
            context['alert_message'] = "Review deleted: "+review_to_delete.title
	else:
	    context['alert_message'] = "You must give your new review a title."
	return render(request, 'ultimatereview/myreviews.html', context)

@login_required
def edit_review(request, review_name_slug):
	review=Review.objects.get(slug=review_name_slug)
	context={'title':review.title, 'slug':review.slug, 'alert_message':None}
	if request.method == 'POST':
		if review!=None:
			if not any(c in '!@#$%^&*\"\'' for c in request.POST.get('review', "")):
				if not Review.objects.filter(slug=slugify(request.POST.get('review', ""))).exists():
					review.title = request.POST.get('review', "")
					review.save()
					reviews = Review.objects.filter(user=request.user).order_by('-date_started')
					context = {'reviews':reviews, 'alert_message':"Review successfully renamed"}
					return render(request, 'ultimatereview/myreviews.html', context)
				else:
					context['alert_message']="A review with this name already exists."
			else:
				context['alert_message']="Title cannot contain !@#$%^&*\"\'"
		else:
			context['alert_message'] = "You must give your review a title."
	return render(request, 'ultimatereview/editreview.html', context)

@login_required
def single_review(request, review_name_slug):
    context = {}

    try:
        # Can we find a review name slug with the given name?
        # If we can't, the .get() method raises a DoesNotExist exception.
        # So the .get() method returns one model instance or raises an exception.
        review = Review.objects.get(slug=review_name_slug)
        context['review_title'] = review.title

        # Retrieve all of the associated pages.
        # Note that filter returns >= 1 model instance.
        queries = Query.objects.filter(review=review)

        # Adds our results list to the template context under name pages.
        context['queries'] = queries
        # We also add the category object from the database to the context dictionary.
        # We'll use this in the template to verify that the category exists.
        context['review'] = review

        if request.method == "POST":
            if not queries.filter(name = request.POST.get('queryField')).exists():
                query = Query.objects.create(review=review, name=request.POST.get('queryField'))
                query.save()
                review = Review.objects.get(slug=review_name_slug)
                queries = Query.objects.filter(review=review)
                context['queries'] = queries
                context['review'] = review

    except Review.DoesNotExist:
        pass

    return render(request, 'ultimatereview/querybuilder.html', context)

@login_required
def abstractPool(request, review_name_slug):
    q = request.method
    if request.method == "POST":
        q = request.POST.get('queryField')
        docList = search.main(q,"relevance","1")
    return HttpResponse(docList)

def AbstractPool(request, review_name_slug):
      if request.method == "POST":
            q = request.POST.get('queryField')
            abstractList = search.main(q,"relevance", "10")
            return render(request, 'ultimatereview/AbstractPool.html', {"Abstracts": abstractList})
      else:
            context_dict = {}
            return render(request, 'ultimatereview/AbstractPool.html', context_dict)



@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)

    # Take the user back to the homepage.
    return HttpResponseRedirect('/ultimatereview/')

def indexQueried(request):
    if request.method == "POST":
        query = request.POST["queryField"]
        abstractList = search.main(query,"relevance","5")
        return HttpResponse(abstractList)
