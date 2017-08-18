"""Models for Table Tennis Rankings."""

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Game(models.Model):
    """Game model, represents a single game."""

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

    def update_rankings(player, opponent, winner):
        """
        Update the ranking for a completed game.

        :param player: The Player object.
        :param opponent: The opposing Player object.
        :param winner: The Player that won the match.
        :return: None, but updates the Player object.

        This follows the ELO ranking method.

        Modify the weighting factor to suit your comp.
        """

        weighting = settings.ELO_WEIGHTING

        player_rank_transformed = 10 ** (player.ranking / 400)
        opponent_rank_transformed = 10 ** (opponent.ranking / 400)
        transformed_sum = player_rank_transformed + opponent_rank_transformed

        player_score = player_rank_transformed / transformed_sum
        opponent_score = opponent_rank_transformed / transformed_sum

        player_s_factor = 1 if winner == player else 0
        opponent_s_factor = 1 if player_s_factor == 0 else 0

        player_rank = player.ranking + weighting * (
            player_s_factor - player_score)
        opponent_rank = opponent.ranking + weighting * (
            opponent_s_factor - opponent_score)

        # Set a floor of 100 for the rankings.
        player_rank = 100 if player_rank < 100 else player_rank
        opponent_rank = 100 if opponent_rank < 100 else opponent_rank

        player.ranking = float('{result:.2f}'.format(result=player_rank))
        player.save()

        opponent.ranking = float('{result:.2f}'.format(result=opponent_rank))
        opponent.save()


@receiver(post_save, sender=User)
def create_player_object(sender, instance, created, **kwargs):
    """Create a player object linked to the User when the user is registered."""
    
    if created:
        Player.objects.create(user=instance)
    instance.player.save()
