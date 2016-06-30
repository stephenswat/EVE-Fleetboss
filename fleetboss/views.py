import re
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from fleetboss.models import Fleet, FleetAccess
from social.apps.django_app.default.models import UserSocialAuth
import requests


def home(request):
    return render(request, 'fleetboss/home.html')


@login_required
@require_POST
@csrf_exempt
def fleet_settings(request, fleet_id):
    obj = get_object_or_404(FleetAccess, id=fleet_id, owner=request.user)
    print(request.POST)
    if 'allow_fleet' in request.POST:
        obj.fleet_access = request.POST['allow_fleet'] == 'true'
        obj.save()
        return HttpResponse(status=200)

    if 'add_viewer' in request.POST:
        user = get_object_or_404(UserSocialAuth, uid=request.POST['add_viewer']).user
        obj.access.add(user)
        return HttpResponse(user.get_full_name(), status=200)

    if 'link_join' in request.POST:
        obj.link_join = request.POST['link_join'] == 'true'
        obj.save()
        return HttpResponse(status=200)

    if 'remove_viewer' in request.POST:
        user = get_object_or_404(UserSocialAuth, uid=request.POST['remove_viewer']).user
        obj.access.remove(user)
        return HttpResponse(status=200)

    return HttpResponse(status=404)


@login_required
def join(request, fleet_id, key):
    fleet_id = int(fleet_id)
    try:
        obj = FleetAccess.objects.get(id=fleet_id, link_join=True, secret=key)
    except FleetAccess.DoesNotExist:
        messages.error(request, "The given key was not valid for the fleet.")
        return redirect(home)

    result = requests.post(
        'https://crest-tq.eveonline.com/fleets/%d/members/' % fleet_id,
        headers={
            'Authorization': 'Bearer ' + obj.owner.access_token,
            'Content-Type': 'application/json'
        },
        json={
            "character": {
                "href": "https://crest-tq.eveonline.com/characters/%d/" %
                request.user.character_id
            },
            "role": "squadMember"
        }
    )

    print(result.status_code)

    if result.status_code != 201:
        if result.json()['key'] == 'FleetCandidateOffline':
            messages.error(request, "You should log in first, dummy.")
        else:
            messages.error(request, "An invite could not be sent to %s." % request.user.get_full_name())
    else:
        messages.success(request, "An invite was successfully sent to %s." % request.user.get_full_name())

    return redirect(home)


@login_required
def fleet(request, fleet_id):
    explicit = False

    try:
        obj = FleetAccess.objects.get(id=fleet_id)
        explicit = request.user == obj.owner or obj.access.filter(pk=request.user.pk).exists()
        if not obj.fleet_access and not explicit:
            messages.error(request, "You do not have access to the requested fleet.")
            return redirect(home)
    except FleetAccess.DoesNotExist:
        obj = FleetAccess(id=fleet_id, owner=request.user)

    for attempt in {obj.owner, request.user}:
        try:
            fleet = Fleet(int(fleet_id), attempt)
            obj.owner = attempt
            obj.save()
            break
        except:
            pass
    else:
        messages.error(request, "API key was not valid for the requested fleet.")
        return redirect(home)

    if not explicit and request.user.get_full_name() not in fleet.member_names:
        messages.error(request, "You do not have access to the requested fleet.")
        return redirect(home)

    return render(
        request, 'fleetboss/fleet.html',
        {'fleet': fleet, 'token': obj, 'owner': obj.owner == request.user})


def parse_url(request):
    if 'url' not in request.GET:
        messages.error(request, "The URL you entered was not of the correct format.")
        return redirect(home)

    match = re.match(r'https://crest-tq.eveonline.com/fleets/(\d+)/|(\d+)',
                     request.GET['url'])

    if not match:
        messages.error(request, "The URL you entered was not of the correct format.")
        return redirect(home)

    return redirect(fleet, fleet_id=int(match.group(1) or match.group(2)))
