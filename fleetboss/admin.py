from django.contrib import admin
from fleetboss.models import Character, FleetAccess


class CharacterAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name')


class FleetAccessAdmin(admin.ModelAdmin):
    list_display = ('id',)


admin.site.register(Character, CharacterAdmin)
admin.site.register(FleetAccess, FleetAccessAdmin)
