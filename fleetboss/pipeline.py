from django.core.exceptions import PermissionDenied, ObjectDoesNotExist


def single_association(backend, user, response, *args, **kwargs):
    try:
        if user.character_id != kwargs['uid']:
            raise PermissionDenied('Cannot associate more than one account.')
    except ObjectDoesNotExist:
        pass
