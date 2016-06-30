from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from fleetboss.models import Fleet, FleetAccess, Character
from fleetboss import settings
from social.apps.django_app.default.models import UserSocialAuth
import json
import re


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

    if 'remove_viewer' in request.POST:
        user = get_object_or_404(UserSocialAuth, uid=request.POST['remove_viewer']).user
        obj.access.remove(user)
        return HttpResponse(status=200)

    return HttpResponse(status=404)

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
        fleet = Fleet(int(fleet_id), attempt)

        if fleet.valid_key:
            obj.owner = attempt
            obj.save()
            break
    else:
        messages.error(request, "API key was not valid for the requested fleet.")
        return redirect(home)

    if not explicit and request.user.get_full_name() not in fleet.member_names:
        messages.error(request, "You do not have access to the requested fleet.")
        return redirect(home)

    return render(
        request, 'fleetboss/fleet.html',
        {'fleet': fleet, 'token': obj, 'owner': obj.owner == request.user})


@login_required
def fleet_json_wings(request, fleet_id):
    fleet = Fleet(int(fleet_id), request.user)
    return JsonResponse(fleet._wings, json_dumps_params={'indent': 4}, safe=False)


@login_required
def fleet_json_members(request, fleet_id):
    fleet = Fleet(int(fleet_id), request.user)
    return JsonResponse(fleet._members, json_dumps_params={'indent': 4}, safe=False)


@login_required
def fleet_json(request, fleet_id):
    fleet = Fleet(int(fleet_id), request.user)
    return JsonResponse(fleet._overview, json_dumps_params={'indent': 4}, safe=False)


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
