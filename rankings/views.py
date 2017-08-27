"""Views for Table Tennis Rankings."""

from collections import Counter

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View
from django.views.generic.edit import CreateView, UpdateView

from rankings.forms import RegistrationForm, TournamentForm
from rankings.models import Game, Group, Player, RankChange, Tournament
from rankings.utils import (
    build_games_from_schedule,
    generate_elimination_games,
    generate_tournament_schedule,
)


class BaseLoginMixin(LoginRequiredMixin):
    """Simple mixin to redirect to the correct login page."""

    login_url = reverse_lazy('ranking_login')


class GroupAdminLoginMixin(BaseLoginMixin):
    """Simple mixin to restrict editing groups to group admins."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        group = get_object_or_404(Group, id=kwargs.get('pk', None))

        if not request.user.player in group.admins.all():
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class TournamentAdminLoginMixin(BaseLoginMixin):
    """Simple mixin to restrict editing tournaments to tournament admins."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        tournament = get_object_or_404(Tournament, id=kwargs.get('pk', None))

        if not request.user.player in tournament.admins.all():
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class IndexView(TemplateView):
    """Main view for site."""

    template_name = 'rankings/index.html'


class RegisterView(CreateView):
    """Simple Registration view."""

    template_name = 'app/register.html'
    form_class = RegistrationForm
    success_url = reverse_lazy('ranking_login')


class PlayerView(BaseLoginMixin, TemplateView):
    """View a single player and all it's games."""

    template_name = 'rankings/players/player.html'

    def get_context_data(self, **kwargs):
        """Compile a list of games for the player."""

        context = super(PlayerView, self).get_context_data(**kwargs)

        player = get_object_or_404(Player, id=self.kwargs.get('pk', None))

        active_games = []
        completed_games = []

        for game in player.games.all().order_by('-date_time'):
            group = game.group_set.first()
            
            if not group:
                continue

            if game.tournament_game:
                # Don't display tournament games in the player profile.
                # These will get displayed in a separate section.
                continue

            if game.active:
                active_games.append({
                    'group': group,
                    'game': game,    
                })
            else:
                completed_games.append({
                    'group': group,
                    'game': game,
                })

        context.update({
            'player': player,
            'groups': player.group_set.all(),
            'active_games': active_games,
            'completed_games': completed_games,
        })

        return context


class GameView(TemplateView):
    """View for a single game for a given group."""

    template_name = 'rankings/groups/game.html'

    def get_context_data(self, **kwargs):
        context = super(GameView, self).get_context_data(**kwargs)

        group = get_object_or_404(Group, id=self.kwargs.get('group_pk', None))
        game = get_object_or_404(Game, id=self.kwargs.get('game_pk', None))
        players = game.players.order_by('-ranking')
        for player in players:
            try:
                rank_change = str(player.rankchange_set.get(game=game))
            except RankChange.DoesNotExist:
                rank_change = 'not available'

            setattr(player, 'rank_change', rank_change)

        context.update({
            'group': group,
            'game': game,
            'players': players,
        })

        return context


class CreateGameView(BaseLoginMixin, CreateView):
    """Create a game for the given group."""

    template_name = 'rankings/groups/create_game.html'
    model = Game
    fields = ['players']

    def form_valid(self, form):
        # Make sure only two players are selected.
        players = form.cleaned_data['players']
        if players.count() != 2:
            form.add_error(
                'players',
                'A game requires two players, please try again.',
            )
            return self.form_invalid(form)

        # Otherwise, connect the game to the group.
        self.object = form.save()
        group = get_object_or_404(Group, id=self.kwargs.get('pk', None))

        group.games.add(self.object)
        group.save()

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy(
            'game', 
            kwargs={
                'group_pk': self.kwargs.get('pk', None),
                'game_pk': self.object.pk,
            },
        )


class FinishGameView(BaseLoginMixin, UpdateView):
    """Finish a game for the given group."""

    template_name = 'rankings/groups/edit_game.html'
    model = Game
    fields = [
        'winner',
        'home_score',
        'away_score',
    ]

    def get_form(self):
        """Restrict the choices for the winner field."""
        form = super(FinishGameView, self).get_form()

        game = get_object_or_404(Game, id=self.kwargs.get('pk', None))

        form.fields['winner'].queryset = game.players

        return form

    def form_valid(self, form):
        game = form.save()
        
        if game.active:
            # Only update the rankings if it's not a tournament game.
            if not game.tournament_game:
                # Update each player's ranking.
                self.update_player_rankings(
                    game, 
                    game.players.first(), 
                    game.players.last(),
                )
            else:
                # For tournament games, if the round robin rounds are finished
                # then we need to generate the elimination rounds. Otherwise,
                # see if we can mark the round robin rounds as finished.
                tournament = game.tournaments.first()

                self.update_tournament(tournament)

            # Mark the game as finished.
            game.active = False
            game.save()

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        """Redirect back to the game's tournament or the game."""

        if self.object.tournaments.first():
            return reverse_lazy(
                'tournament',
                kwargs={
                    'pk': self.object.tournaments.first().pk,
                },
            )
        else:
            return reverse_lazy(
                'game', 
                kwargs={
                    'group_pk': self.object.group_set.first().pk,
                    'game_pk': self.object.pk,
                },
            )

    @staticmethod
    def update_player_rankings(game, player_1, player_2):
        """
        Update rankings for the players in the game.
        
        :param game: The Game object being saved.
        :param player_1: The first Player object for the game.
        :param player_2: The second Player object for the game.
        :return: None.
        """

        loser = player_1 if player_1 != game.winner else player_2

        player_1_change = RankChange(game=game, player=player_1,
                                     before=player_1.ranking)
        player_2_change = RankChange(game=game, player=player_2,
                                     before=player_2.ranking)
        Player.update_rankings(
            game.winner,
            loser
        )
        # Players were saved through
        # winner/loser instances, must reload.
        player_1.refresh_from_db()
        player_2.refresh_from_db()

        player_1_change.after = player_1.ranking
        player_2_change.after = player_2.ranking

        player_1_change.save()
        player_2_change.save()

    @staticmethod
    def update_tournament(tournament):
        """
        Update the tournament.
        
        :param tournament: The Tournament object.
        :return: None.
        """

        active_games = tournament.games.filter(active=True)

        # This is called prior to saving the last active game.
        if active_games.count() <= 1:
            if not tournament.round_robin_finished:
                # Mark the round robin phase as finished.
                tournament.round_robin_finished = True
                tournament.save()

            if (tournament.has_elimination and 
                    tournament.round_robin_finished):
                # Either generate the elimination rounds or crown the 
                # winner of the tournament.
                no_players = (
                    tournament.no_players_for_elimination_rounds)

                if tournament.games.filter(elimination_game=True):
                    # Elimination games already exist, create a new 
                    # round of eliminations from the winners if 
                    # possible (i.e. there are rounds/players left).
                    if no_players >= 2:
                        elimination_games = tournament.games.filter(
                            elimination_game=True,
                        )

                        generate_elimination_games(
                            tournament,
                            elimination_games,
                            no_players,
                        )
                else:
                    # No elimination games, create the first round.
                    generate_elimination_games(
                        tournament,
                        tournament.games.all(),
                        no_players,
                    )

                # Reduce the number of players for elimination 
                # rounds by 2 for the next iteration.
                if no_players >= 2:
                    # Refresh the tournament from the database as it's 
                    # been modified in another module.
                    tournament.refresh_from_db()

                    tournament.no_players_for_elimination_rounds = (
                        no_players - 2)

                    tournament.save()

            # The tournament is over when the round robin phase is 
            # finished and there are no players left for elimination 
            # (either by having no elimination rounds or by playing all 
            # elimination rounds).
            if (tournament.round_robin_finished and 
                    tournament.no_players_for_elimination_rounds == 0):
                tournament.active = False
                tournament.save()

class GroupsView(TemplateView): 
    """View the groups."""

    template_name = 'rankings/groups/groups.html'

    def get_context_data(self, **kwargs):
        context = super(GroupsView, self).get_context_data(**kwargs)

        context['groups'] = Group.objects.all()

        return context


class GroupView(TemplateView):
    """View a single group and all it's players."""

    template_name = 'rankings/groups/group.html'

    def get_context_data(self, **kwargs):
        context = super(GroupView, self).get_context_data(**kwargs)

        group = get_object_or_404(Group, id=self.kwargs.get('pk', None))

        context.update({
            'group': group,
            'players': group.players.order_by('-ranking'),
            'active_games': group.games.filter(active=True).order_by('-date_time'),
            'completed_games': group.games.filter(active=False).order_by('-date_time'),
        })

        return context


class JoinGroupView(BaseLoginMixin, View):
    """Enable logged in user to join a group."""

    def get(self, request, *args, **kwargs):

        group = get_object_or_404(Group, id=kwargs.get('pk', None))

        player = request.user.player

        if player not in group.players.all():
            group.players.add(player)
            group.save()

            return HttpResponseRedirect(
                reverse_lazy('group', kwargs={'pk': group.pk}))

        return HttpResponseRedirect(reverse_lazy('groups'))


class EditGroupView(GroupAdminLoginMixin, SuccessMessageMixin, UpdateView):
    """Simple EditView for editing a group."""
    
    template_name = 'rankings/groups/edit_group.html'
    model = Group
    fields = [
        'name',
        'players',
    ]

    def get_success_url(self):
        return reverse_lazy('group', kwargs={'pk': self.object.pk})
    
    def get_success_message(self, cleaned_data):
        name = cleaned_data.get('name')

        return f'{name} was edited successfully'


class TournamentsView(TemplateView): 
    """View the tournaments."""

    template_name = 'rankings/tournaments/tournaments.html'

    def get_context_data(self, **kwargs):
        context = super(TournamentsView, self).get_context_data(**kwargs)

        context['tournaments'] = Tournament.objects.all()

        return context


class TournamentView(TemplateView):
    """View a single tournament and all it's players and games."""

    template_name = 'rankings/tournaments/tournament.html'

    def get_context_data(self, **kwargs):
        context = super(TournamentView, self).get_context_data(**kwargs)

        tournament = get_object_or_404(
            Tournament, id=self.kwargs.get('pk', None))

        # Get the players and add the number of games they have won.
        players = tournament.players.order_by('user__username')
        counter = Counter(
            game.winner for game in tournament.games.all()
        )
        for player in players:
            setattr(player, 'wins', counter.get(player, 0))

        # Sort by wins (descending).
        players = sorted(players, key=lambda p: p.wins, reverse=True)

        context.update({
            'tournament': tournament,
            'players': players,
            'active_games': tournament.games.filter(active=True).order_by(
                '-date_time'),
            'completed_games': tournament.games.filter(active=False).order_by(
                '-date_time'),
        })

        return context


class JoinTournamentView(BaseLoginMixin, View):
    """Enable logged in user to join a tournament."""

    def get(self, request, *args, **kwargs):

        tournament = get_object_or_404(Tournament, id=kwargs.get('pk', None))

        player = request.user.player

        if player not in tournament.players.all():
            tournament.players.add(player)
            tournament.save()

            return HttpResponseRedirect(
                reverse_lazy('tournament', kwargs={'pk': tournament.pk}))

        return HttpResponseRedirect(reverse_lazy('tournaments'))


class EditTournamentView(
    TournamentAdminLoginMixin, 
    SuccessMessageMixin, 
    UpdateView,
):
    """Simple EditView for editing a tournament."""
    
    template_name = 'rankings/tournaments/edit_tournament.html'
    model = Tournament
    form_class = TournamentForm

    def get_success_url(self):
        return reverse_lazy('tournament', kwargs={'pk': self.object.pk})
    
    def get_success_message(self, cleaned_data):
        name = cleaned_data.get('name')

        return f'{name} was edited successfully'



class StartTournamentView(TournamentAdminLoginMixin, View):
    """Simple view to start a tournament and generate the games."""

    def get(self, request, *args, **kwargs):
        """Start the tournament, generate the games and redirect."""

        tournament = get_object_or_404(
            Tournament, id=self.kwargs.get('pk', None))

        if tournament.has_round_robin:
            # Generate the round robin games.
            if tournament.players.count() % 2 == 1:
                messages.error(
                    request, 
                    'There must be an even number of players for a tournament.',
                )
            else:
                # Generate the schedule from the competing players and number
                # of rounds of round robin games.
                competing_players = list(tournament.players.all())
                schedule = generate_tournament_schedule(
                    competing_players,
                    tournament.no_round_robin_rounds,
                )

                # Create games for each pair of players for the tournament.
                build_games_from_schedule(tournament, schedule)

        return HttpResponseRedirect(
                reverse_lazy('tournament', kwargs={'pk': tournament.pk}))


class TournamentGameView(TemplateView):
    """View for a single game for a given tournament."""

    template_name = 'rankings/tournaments/game.html'

    def get_context_data(self, **kwargs):
        context = super(TournamentGameView, self).get_context_data(**kwargs)

        tournament = get_object_or_404(
            Tournament, id=self.kwargs.get('tournament_pk', None))
        game = get_object_or_404(Game, id=self.kwargs.get('game_pk', None))
        players = game.players.order_by('user__username')

        context.update({
            'tournament': tournament,
            'game': game,
            'players': players,
        })

        return context
