"""Models for Table Tennis Rankings."""

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from rankings.elo import elo


class Game(models.Model):
    """Game model, represents a single game."""
    date_time = models.DateTimeField(
        auto_now_add=True,
    )

    players = models.ManyToManyField(
        'Player',
        related_name='games',
        blank=True,
    )
    active = models.BooleanField(
        default=True,
    )
    winner = models.ForeignKey(
        'Player',
        related_name='winning_games',
        blank=True,
        null=True,
    )
    home_score = models.IntegerField(
        blank=True,
        null=True,
    )
    away_score = models.IntegerField(
        blank=True,
        null=True,
    )

    def __str__(self):
        id_ = self.pk
        winner = self.winner

        if winner:
            return f'Game {id_}: won by {winner}'

        return f'Game {id_}: in progress'


class Group(models.Model):
    """Group model, for a group of players."""

    name = models.CharField(
        max_length=255,
        help_text='Enter the group name',
        unique=True,
    )
    players = models.ManyToManyField(
        'Player',
        blank=True,
    )
    games = models.ManyToManyField(
        Game,
        blank=True,
    )
    admins = models.ManyToManyField(
        'Player',
        related_name='group_admins',
        blank=True,
    )

    def __str__(self):
        name = self.name
        return f'{name}'


class Player(models.Model):
    """User profile for players."""

    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
    )
    ranking = models.FloatField(
        default=1000,
    )

    def __str__(self):
        if self.user.get_full_name():
            return self.user.get_full_name()
        else:
            return self.user.username

    @staticmethod
    def update_rankings(winner, loser):
        """
        Update the ranking for a completed game.

        :param winner: The Player that won the match.
        :param loser: The Player that lost the match.
        :return: None, but updates the Player object.

        This follows the ELO ranking method.

        Modify the weighting factor to suit your comp.
        """
        weighting = settings.ELO_WEIGHTING
        winner.ranking, loser.ranking = elo(winner.ranking, loser.ranking, weighting)
        winner.save()
        loser.save()


class RankChange(models.Model):
    player = models.ForeignKey(Player)
    game = models.ForeignKey(Game)
    before = models.FloatField()
    after = models.FloatField()

    def __str__(self):
        delta = self.after - self.before
        return f'{self.after:.2f} ({delta:.2f})'


@receiver(post_save, sender=User)
def create_player_object(sender, instance, created, **kwargs):
    """Create a player object linked to the User when the user is registered."""
    
    if created:
        Player.objects.create(user=instance)
    instance.player.save()
