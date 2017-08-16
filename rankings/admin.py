"""Admin forms and views for Rankings app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from rankings.models import Game, Group, Player


class PlayerInline(admin.StackedInline):
    """Admin Inline for Player objects."""

    model = Player
    can_delete = False


class UserAdmin(BaseUserAdmin):
    """User Admin view."""

    inlines = [
        PlayerInline,
    ]


class GameAdmin(admin.ModelAdmin):
    """Admin for Game Objects."""

    model = Game


class GroupAdmin(admin.ModelAdmin):
    """Admin for Group Objects."""

    model = Group


class PlayerAdmin(admin.ModelAdmin):
    """Admin for Player Objects."""

    model = Player


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Player, PlayerAdmin)
