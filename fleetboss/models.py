from django.db import models
from django.utils.functional import cached_property
from django.contrib.auth.models import AbstractUser
from social.apps.django_app.utils import load_strategy
from fleetboss import settings, ships
from datetime import datetime, timedelta
from collections import OrderedDict, Counter
import json
import requests


class Character(AbstractUser):
    @property
    def character_id(self):
        return self.__crest['id']

    @property
    def access_token(self):
        return self.__crest['access_token']

    @cached_property
    def __crest(self):
        provider = self.social_auth.get(provider='eveonline')

        difference = (datetime.strptime(
            provider.extra_data['expires'],
            "%Y-%m-%dT%H:%M:%S"
        ) - datetime.now()).total_seconds()

        if (difference < 10):
            provider.refresh_token(load_strategy())
            expiry = datetime.now() + timedelta(seconds=1200)
            provider.extra_data['expires'] = expiry.strftime("%Y-%m-%dT%H:%M:%S")
            provider.save()

        return provider.extra_data


class FleetAccess(models.Model):
    id = models.IntegerField(primary_key=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, related_name='fleets_owned')
    access = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='fleets_accessible', blank=True)
    fleet_access = models.BooleanField(default=False)


class FleetMember(object):
    def __init__(self, name, id, **_):
        self.name = name
        self.id = id


class Squad(object):
    def __init__(self, id, name, **_):
        self.id = id
        self.commander = None
        self.members = []
        self.name = name

    def add_member(self, character):
        self.members.append(character)

    def add_commander(self, character):
        self.commander = character

    def __iter__(self):
        return self.members.__iter__()

    def __len__(self):
        return len(self.members)


class Wing(object):
    def __init__(self, id, name, squadsList, **_):
        self.id = id
        self.commander = None
        self.squads = {}
        self.name = name

        for squad in squadsList:
            self.squads[squad['id']] = Squad(**squad)

    def add_member(self, squad_id, character, commander=False):
        if commander:
            self.squads[squad_id].add_commander(character)
        else:
            self.squads[squad_id].add_member(character)

    def add_commander(self, character):
        self.commander = character

    @property
    def member_count(self):
        return sum(len(squad) for squad in self)

    def __len__(self):
        return len(self.squads)

    def __iter__(self):
        return self.squads.values().__iter__()


class Fleet(object):
    def __init__(self, fleet_id, owner):
        self.id = fleet_id
        self.owner = owner
        self.commander = None
        self.__wings = None

    @cached_property
    def _overview(self):
        return self.__request('')[1]

    @cached_property
    def _members(self):
        return self.__request('members')[1]['items']

    @cached_property
    def _wings(self):
        return self.__request('wings')[1]['items']

    @property
    def boss(self):
        for p in self._members:
            if '(Boss)' in p['roleName']:
                return p['character']['name']

    @property
    def is_freemove(self):
        return self._overview['isFreeMove']

    @property
    def is_advertised(self):
        return self._overview['isRegistered']

    @property
    def composition_class(self):
        return dict(Counter(p['ship']['name'] for p in self._members))

    @property
    def composition_category(self):
        res = {}

        for name, count in self.composition_class.items():
            category = ships.categories.get(name, 'Unknown')
            if category not in res:
                res[category] = 0
            res[category] += count

        return res

    @property
    def composition_size(self):
        res = {}

        for name, count in self.composition_category.items():
            size = ships.sizes.get(name, 'Unknown')
            if size not in res:
                res[size] = 0
            res[size] += count

        return res

    @property
    def location_system(self):
        return dict(Counter(p['solarSystem']['name'] for p in self._members))

    @property
    def location_docked(self):
        return dict(Counter('Docked' if 'station' in p else 'Undocked' for p in self._members))

    @property
    def warnings(self):
        res = []

        if self.commander is None:
            res.append(('warning', 'The fleet has no commander.'))

        for wing in self.wings:
            if wing.member_count == 0:
                continue

            if not wing.commander and len(wing) > 1:
                res.append(('warning', 'Wing <em>%s</em> has no commander.' % wing.name))

            for squad in wing:
                if not squad.commander and len(squad) > 0:
                    res.append(('warning', 'Squad <em>%s</em> of wing <em>%s</em> has no commander.' % (squad.name, wing.name)))

        return res

    @property
    def wings(self):
        if self.__wings is not None:
            return self.__wings.values()

        res = {}

        for w in self._wings:
            res[w['id']] = Wing(**w)

        for p in self._members:
            member = FleetMember(**p['character'])

            if p['wingID'] < 0:
                self.commander = member

            if p['squadID'] < 0:
                res[p['wingID']].add_commander(member)
            else:
                res[p['wingID']].add_member(p['squadID'], member, p['roleID'] == 3)

        self.__wings = res
        return self.__wings.values()

    @property
    def member_names(self):
        for p in self._members:
            yield p['character']['name']

    @property
    def squad_count(self):
        return sum(len(wing) for wing in self.wings)

    @property
    def member_count(self):
        return len(self._members)

    @property
    def valid_key(self):
        try:
            self._overview
            return True
        except RuntimeError:
            return False

    def __request(self, url):
        result = requests.get(
            'https://crest-tq.eveonline.com/fleets/%d/%s' % (self.id, url + '/' if len(url) > 0 else ''),
            headers={
                'Authorization': 'Bearer ' + self.owner.access_token,
                'Host': 'crest-tq.eveonline.com'}
        )

        if result.status_code != 200:
            raise RuntimeError("CREST call returned a non-200 status code.")

        return result.status_code, result.json()

    def __iter__(self):
        return self.wings.values().__iter__()

    def __len__(self):
        return len(self.wings)
