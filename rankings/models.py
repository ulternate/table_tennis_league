"""Models for Table Tennis Rankings."""

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from rankings.utils import elo


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
    tournament_game = models.BooleanField(
        default=False,
    )
    elimination_game = models.BooleanField(
        default=False,
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

        return f'Game {id_}: {self.players.first()} vs {self.players.last()}'


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


class Tournament(models.Model):
    """Tournament model, store the tournament configuration."""
    active = models.BooleanField(
        default=True,
    )
    name = models.CharField(
        max_length=255,
        help_text="Enter the tournament name",
    )
    has_round_robin = models.BooleanField(
        verbose_name="Are there Round Robin rounds?",
    )
    no_round_robin_rounds = models.PositiveIntegerField(
        verbose_name="Number of Round Robin rounds",
        default=0,
    )
    round_robin_finished = models.BooleanField(
        default=False,
    )
    has_elimination = models.BooleanField(
        verbose_name="Are there Elimination rounds?",
    )
    no_players_for_elimination_rounds = models.PositiveIntegerField(
        verbose_name="Number of players for Elimination rounds",
        default=0,
    )
    games = models.ManyToManyField(
        Game,
        related_name="tournaments",
        blank=True,
    )
    players = models.ManyToManyField(
        Player,
        related_name="tournaments",
        blank=True,
    )    
    admins = models.ManyToManyField(
        Player,
        related_name='tournament_admins',
        blank=True,
    )

    def __str__(self):
        return self.name


@receiver(post_save, sender=User)
def create_player_object(sender, instance, created, **kwargs):
    """Create a player object linked to the User when the user is registered."""
    
    if created:
        Player.objects.create(user=instance)
    instance.player.save()
