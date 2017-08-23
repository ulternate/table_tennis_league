"""Views for Table Tennis Rankings."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View
from django.views.generic.edit import CreateView, UpdateView

from rankings.forms import RegistrationForm
from rankings.models import Game, Group, Player, RankChange


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
        game = form.save(commit=False)
        # Only update the game and rankings if it's active.
        if game.active:
            # Update each player's ranking.
            player_1 = game.players.first()
            player_2 = game.players.last()

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
            # Mark the game as finished.
            game.active = False
            game.save()

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        """Redirect back to the game."""

        return reverse_lazy(
            'game', 
            kwargs={
                'group_pk': self.object.group_set.first().pk,
                'game_pk': self.object.pk,
            },
        )


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
