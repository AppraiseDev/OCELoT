"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

Non-format field validators (team name, institution, publication, token).
"""
import re

from django.core.exceptions import ValidationError


def validate_team_name(value):
    """Validates team name matches r'^[a-zA-Z0-9_\\- ]{2,32}$'."""
    valid_name = re.compile(r'^[a-zA-Z0-9_\- ]{2,32}$')
    if not valid_name.match(value):
        _msg = 'Team name must match regexp r"^[a-zA-Z0-9_\\- ]{2,32}$"'
        raise ValidationError(_msg)


def validate_institution_name(value):
    """Validates institution name: UTF-8 Latin script or LaTeX escape
    sequences.
    """
    valid_name = re.compile(r'^[\u0000-\u017F]{2,32}$')
    if not valid_name.match(value):
        _msg = (
            'Institution name must consist only of UTF-8 Latin script '
            'or LaTeX escape sequences, and max 32 characters.'
        )
        raise ValidationError(_msg)


def validate_publication_name(value):
    """Validates short publication name: ASCII letters, digits, dot, dash
    and underscore, no whitespace.
    """
    # Keeping max 32 characters for backward compatibility
    valid_name = re.compile(r'^[a-zA-Z0-9_\-.]{2,32}$')
    if not valid_name.match(value):
        _msg = 'Short publication name must match regexp r"^[a-zA-Z0-9._\\-.]{2,12}$"'
        raise ValidationError(_msg)


def validate_token(value):
    """Validates token matches r'[a-f0-9]{10}'."""
    valid_token = re.compile(r'[a-f0-9]{10}')
    if not valid_token.match(value):
        _msg = 'Token must match regexp r"[a-f0-9]{10}"'
        raise ValidationError(_msg)
