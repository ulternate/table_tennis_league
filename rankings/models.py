from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Game(models.Model):
    """Game model, represents a single game."""

    players = models.ManyToManyField(
        'Player',
        related_name='game_players',
        blank=True,
    )
    active = models.BooleanField(
        default=True,
    )
    winner = models.OneToOneField(
        'Player',
        related_name='game_winner',
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


class Group(models.Model):
    """Group model, for a group of players."""

    name = models.CharField(
        max_length=255,
        help_text='Enter the group name',
    )
    players = models.ManyToManyField(
        'Player',
        blank=True,
    )
    games = models.ManyToManyField(
        Game,
        blank=True,
    )


class Player(models.Model):
    """User profile for players."""

    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
    )
    ranking = models.FloatField(
        default=1000,
    )
