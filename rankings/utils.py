"""Utility functions for rankings app."""

from collections import Counter


def elo(winner_rank, loser_rank, weighting):
    """
    :param winner: The Player that won the match.
    :param loser: The Player that lost the match.
    :param weighting: The weighting factor to suit your comp.
    :return: (winner_new_rank, loser_new_rank) Tuple.

    This follows the ELO ranking method.
    """
    winner_rank_transformed = 10 ** (winner_rank / 400)
    opponent_rank_transformed = 10 ** (loser_rank / 400)
    transformed_sum = winner_rank_transformed + opponent_rank_transformed

    winner_score = winner_rank_transformed / transformed_sum
    loser_score = opponent_rank_transformed / transformed_sum

    winner_rank = winner_rank + weighting * (
        1 - winner_score)
    loser_rank = loser_rank - weighting * loser_score

    # Set a floor of 100 for the rankings.
    winner_rank = 100 if winner_rank < 100 else winner_rank
    loser_rank = 100 if loser_rank < 100 else loser_rank

    winner_rank = float('{result:.2f}'.format(result=winner_rank))
    loser_rank = float('{result:.2f}'.format(result=loser_rank))

    return winner_rank, loser_rank


def generate_tournament_schedule(competing_players, rounds):
    """
    Generate either the round robin or elimination rounds from the players list.

    :param competing_players: A list of Player objects for the tournament.
    :param rounds: int, number of rounds to generate matches for.
    :return: A list of Player object pairs to be used to create games for each
        pair.
    """

    schedule = []

    for i in range(rounds):
        mid = int(len(competing_players) / 2)
        first_half = list(competing_players[:mid])
        second_half = list(competing_players[mid:])
        second_half.reverse()

        # Switch sides after each round.
        if(i % 2 == 1):
            schedule = schedule + list(zip(first_half, second_half))
        else:
            schedule = schedule + list(zip(second_half, first_half))

        # Rotate the lists by putting the last player at index 1.
        competing_players.insert(1, competing_players.pop())

    return schedule


def build_games_from_schedule(tournament, schedule, elimination=False):
    """
    Build Game objects from the given schedule for the tournament.

    :param tournament: The Tournament object.
    :param schedule: A list of Player object pairs.
    :param elimination: Whether the game is an elimination game or not.
    :return None, the tournament object will have games added to it.
    """

    from .models import Game  # Import fails at module level.

    for scheduled_game in schedule:
        game = Game(tournament_game=True)
        if elimination:
            game.elimination_game = True
        game.save()
        
        for player in scheduled_game:
            game.players.add(player)
        
        game.save()

        # Add the game to the tournament.
        tournament.games.add(game)
        tournament.save()


def generate_elimination_games(tournament, games, no_players):
    """
    Generate the games for elimination rounds.
    
    :param tournament: The Tournament object.
    :param games: A queryset of games for calculating the placings.
    :param no_players: An int, the number of players going through.
    :return: None, elimination finals will be generated.
    """
    
    counter = Counter(game.winner for game in games)

    finalists = [finalist[0] for finalist in counter.most_common(no_players)]

    schedule = generate_tournament_schedule(finalists, rounds=1)

    build_games_from_schedule(tournament, schedule, elimination=True)
