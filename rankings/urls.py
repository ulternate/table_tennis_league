"""Urls for Table Tennis Rankings."""

from django.conf.urls import url

from rankings.views import (
    CreateGameView,
    EditGroupView,
    FinishGameView,
    GameView,
    GroupView,
    GroupsView,
    IndexView,
    JoinGroupView,
    PlayerView,
)   

urlpatterns = [
    url(
        r'^$',
        IndexView.as_view(), 
        name='index',
    ),
    url(
        r'finish_game/(?P<pk>\d+)/$',
        FinishGameView.as_view(),
        name='finish_game',
    ),
    url(
        r'^groups/$',
        GroupsView.as_view(),
        name='groups',
    ),
    url(
        r'^groups/(?P<pk>\d+)/$',
        GroupView.as_view(),
        name='group',
    ),
    url(
        r'^groups/(?P<pk>\d+)/join/$',
        JoinGroupView.as_view(),
        name='join_group',
    ),
    url(
        r'groups/(?P<group_pk>\d+)/game/(?P<game_pk>\d+)/$',
        GameView.as_view(),
        name='game',
    ),
    url(
        r'groups/(?P<pk>\d+)/create_game/$',
        CreateGameView.as_view(),
        name='create_game',
    ),
    url(
        r'^groups/edit_group/(?P<pk>\d+)/$',
        EditGroupView.as_view(),
        name='edit_group',
    ),
    url(
        r'^players/(?P<pk>\d+)/$',
        PlayerView.as_view(),
        name='player_profile',
    ),
]
