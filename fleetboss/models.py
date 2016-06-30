from datetime import datetime, timedelta
from collections import Counter
from django.db import models
from django.utils.functional import cached_property
from django.contrib.auth.models import AbstractUser
from social.apps.django_app.utils import load_strategy
from fleetboss import settings, ships
import requests


class Character(AbstractUser):
    """
    A database model which is used by the EVE Online SSO to create, store and
    check logins. Stores information from the EVE API such as the character ID.
    """

    @property
    def character_id(self):
        """
        Returns the EVE ID of the character.
        """

        return self.__crest['id']

    @property
    def access_token(self):
        """
        Returns the access token which can be used for CREST calls.
        """

        return self.__crest['access_token']

    @cached_property
    def __crest(self):
        """
        Helper function to occasionally refresh the access token whenever it
        expires.
        """

        provider = self.social_auth.get(provider='eveonline')

        difference = (datetime.strptime(
            provider.extra_data['expires'],
            "%Y-%m-%dT%H:%M:%S"
        ) - datetime.now()).total_seconds()

        if difference < 10:
            provider.refresh_token(load_strategy())
            expiry = datetime.now() + timedelta(seconds=1200)
            provider.extra_data['expires'] = expiry.strftime("%Y-%m-%dT%H:%M:%S")
            provider.save()

        return provider.extra_data


class FleetAccess(models.Model):
    """
    Database model which stores the access settings of a fleet. Includes the
    owner, any characters with view access and the option to make it accessible
    to the entire fleet.
    """

    id = models.IntegerField(primary_key=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                              related_name='fleets_owned')
    access = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
                                    related_name='fleets_accessible')
    fleet_access = models.BooleanField(default=False)


class FleetMember(object):
    """
    Simple data-only class that respresents a single capsuleer.
    """

    def __init__(self, name, id, **_):
        self.name = name
        self.id = id


class Squad(object):
    """
    A squad in a fleet which has a name, a commander and up to 10 members.
    """

    def __init__(self, id, name, **_):
        self.id = id
        self.commander = None
        self.members = []
        self.name = name

    def add_member(self, character):
        """
        Adds a single member to the fleet.
        """

        self.members.append(character)

    def __iter__(self):
        return self.members.__iter__()

    def __len__(self):
        return len(self.members)


class Wing(object):
    """
    A single wing in a fleet which can contain in turn five squads as well as a
    commander.
    """

    def __init__(self, id, name, squadsList, **_):
        self.id = id
        self.commander = None
        self.squads = {}
        self.name = name

        for squad in squadsList:
            self.squads[squad['id']] = Squad(**squad)

    def add_member(self, squad_id, character, commander=False):
        """
        Add a member to the wing which is in turn passed to the squad.
        """

        if commander:
            self.squads[squad_id].commander = character
        else:
            self.squads[squad_id].add_member(character)

    @property
    def member_count(self):
        """
        Returns the number of members in the squads of this wing.
        """

        return sum(len(squad) for squad in self)

    def __len__(self):
        return len(self.squads)

    def __iter__(self):
        return self.squads.values().__iter__()


class Fleet(object):
    """
    An entire fleet. Contains up to five wings, a commander as well as an API
    key provided by a used which is used to get information.
    """

    def __init__(self, fleet_id, owner):
        self.id = fleet_id
        self.owner = owner
        self.commander = None
        self.__wings = {}

        for wing in self._wings:
            self.__wings[wing['id']] = Wing(**wing)

        for p in self._members:
            member = FleetMember(**p['character'])

            if p['wingID'] < 0:
                self.commander = member
                continue

            if p['squadID'] < 0:
                self.__wings[p['wingID']].commander = member
            else:
                self.__wings[p['wingID']].add_member(p['squadID'], member, p['roleID'] == 3)

    @cached_property
    def _overview(self):
        """
        Return a cached overview directly from the CREST endpoint.
        """

        return self.__request('')[1]

    @cached_property
    def _members(self):
        """
        Return a cached list of members directly from the CREST endpoint.
        """

        return self.__request('members')[1]['items']

    @cached_property
    def _wings(self):
        """
        Return a cached list of wings from the CREST endpoint.
        """

        return self.__request('wings')[1]['items']

    @property
    def boss(self):
        """
        Return the name of the fleet boss (not the commander).
        """

        for p in self._members:
            if '(Boss)' in p['roleName']:
                return p['character']['name']

    @property
    def is_freemove(self):
        """
        Returns true if members are free to move around positions in the fleet
        or false otherwise.
        """

        return self._overview['isFreeMove']

    @property
    def is_advertised(self):
        """
        Returns true if an advertisement for the fleet is up or false
        otherwise.
        """

        return self._overview['isRegistered']

    @property
    def composition_class(self):
        """
        A dictionary of different ship types in the fleet with the number of
        instances per ship type.
        """

        return dict(Counter(p['ship']['name'] for p in self._members))

    @property
    def composition_category(self):
        """
        A somewhat broader counting of ships bucketed by category.
        """

        res = {}

        for name, count in self.composition_class.items():
            category = ships.CATEGORIES.get(name, 'Unknown')
            if category not in res:
                res[category] = 0
            res[category] += count

        return res

    @property
    def composition_size(self):
        """
        Even broader than the catagory buckets, the size of the ship hulls in
        the fleet.
        """

        res = {}

        for name, count in self.composition_category.items():
            size = ships.SIZES.get(name, 'Unknown')
            if size not in res:
                res[size] = 0
            res[size] += count

        return res

    @property
    def location_system(self):
        """
        Returns buckets for different solar systems in which the fleet members
        are located.
        """

        return dict(Counter(p['solarSystem']['name'] for p in self._members))

    @property
    def location_docked(self):
        """
        Buckets for the docking status of fleet memebers, either docked or
        undocked.
        """
        return dict(Counter('Docked' if 'station' in p else 'Undocked'
                            for p in self._members))

    @property
    def warnings(self):
        """
        Returns a list of warnings and other notifications about the fleet.
        """

        res = []

        if self.commander is None and len(self) > 1:
            res.append(('warning', 'The fleet has no commander.'))

        for wing in self:
            if wing.member_count == 0:
                continue

            if not wing.commander and len(wing) > 1:
                res.append(('warning', 'Wing <em>%s</em> has no commander.' % wing.name))

            for squad in wing:
                if not squad.commander and len(squad) > 0:
                    res.append(('warning', 'Squad <em>%s</em> of wing <em>%s</em> has no commander.' % (squad.name, wing.name)))

        return res

    @property
    def member_names(self):
        """
        A list of names of members of the fleet.
        """

        for p in self._members:
            yield p['character']['name']

    @property
    def squad_count(self):
        """
        Returns the number of squads in the fleet.
        """

        return sum(len(wing) for wing in self)

    @property
    def member_count(self):
        """
        Returns the number of members in this fleet.
        """

        return len(self._members)

    def __request(self, url):
        """
        A way of performing CREST API calls with the access token of the person
        registered as the owner of the fleet.
        """

        result = requests.get(
            'https://crest-tq.eveonline.com/fleets/%d/%s' % (
                self.id, url + '/' if len(url) > 0 else ''),
            headers={
                'Authorization': 'Bearer ' + self.owner.access_token,
                'Host': 'crest-tq.eveonline.com'}
        )

        if result.status_code != 200:
            raise RuntimeError("CREST call returned a non-200 status code.")

        return result.status_code, result.json()

    def __iter__(self):
        return self.__wings.values().__iter__()

    def __len__(self):
        return len(self.__wings)
