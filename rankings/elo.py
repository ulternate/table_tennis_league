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
