"""Forms for Rankings app."""

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import ModelForm, ValidationError

from rankings.models import Tournament


class RegistrationForm(UserCreationForm):
    """Simple Registration Form."""

    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
        ]


class TournamentForm(ModelForm):
    """Simple Tournament Form."""

    class Meta:
        model = Tournament
        exclude = [
            'admins',
            'games',
            'round_robin_finished',
        ]

    def clean(self):
        # Clean the form, setting the numbers to zero if there are no round 
        # robin rounds or elimination rounds.
        
        cleaned_data = super(TournamentForm, self).clean()

        if (not cleaned_data['has_round_robin'] and not 
                cleaned_data['has_elimination']):
            raise ValidationError(
                'There must be either round robin rounds or elimination rounds '
                'or both.'
            )

        if not cleaned_data['has_round_robin']:
            # Set the number of round robin rounds to zero.
            cleaned_data['no_round_robin_rounds'] = 0
        elif cleaned_data['no_round_robin_rounds'] == 0:
            raise ValidationError(
                'You must have more than zero rounds of round robin if you are '
                ' having a round robin component.'
            )

        if not cleaned_data['has_elimination']:
            # Set the number of elimination rounds to zero.
            cleaned_data['no_players_for_elimination_rounds'] = 0
        elif cleaned_data['no_players_for_elimination_rounds'] == 0:
            raise ValidationError(
                'You must have more than zero rounds of elimination if you are '
                ' having an elimination component.'
            )

        return cleaned_data
