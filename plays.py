from __future__ import division, print_function

from collections import OrderedDict

import numpy as np


def kneel_down(score_diff, timd, secs_left, dwn):
    """Return 1 if the offense can definitely kneel out the game,
    else return 0."""

    if score_diff <= 0 or dwn == 4:
        return 0

    if timd == 0 and secs_left <= 120 and dwn == 1:
        return 1
    if timd == 1 and secs_left <= 87 and dwn == 1:
        return 1
    if timd == 2 and secs_left <= 48 and dwn == 1:
        return 1

    if timd == 0 and secs_left <= 84 and dwn == 2:
        return 1
    if timd == 1 and secs_left <= 45 and dwn == 2:
        return 1

    if timd == 0 and secs_left <= 42 and dwn == 3:
        return 1

    return 0


def change_poss(situation, play_type, features, **kwargs):
    """Handles situation updating for all plays that involve
    a change of possession, including punts, field goals,
    missed field goals, touchdowns, turnover on downs.

    Parameters
    ----------
    situation : OrderedDict
    play_type : function
    features  : list[str]

    Returns
    -------
    new_situation : OrderedDict
    """

    new_situation = OrderedDict.fromkeys(features)

    # Nearly all changes of possession result in a 1st & 10
    # Doesn't cover the edge case of a turnover within own 10 yardline.
    new_situation['dwn'] = 1
    new_situation['ytg'] = 10

    # Assumes 10 seconds of game clock have elapsed per play
    # Could tune this.
    new_situation['secs_left'] = max([situation['secs_left'] - 10, 0])
    new_situation['qtr'] = qtr(new_situation['secs_left'])

    # Assign timeouts to the correct teams
    new_situation['timo'], new_situation['timd'] = (
            situation['timd'], situation['timo'])

    # Valid types are turnover_downs, punt, field_goal,
    # missed_field_goal, touchdown

    # Any score changes are handled here
    new_situation = play_type(situation, new_situation, **kwargs)

    # Change sign on spread, recompute over-under
    new_situation['spread'] = -1 * situation['spread'] + 0

    # Avoid negative zeros
    if new_situation.get('score_diff') is None:
        new_situation['score_diff'] = int(-1 * situation['score_diff'])
    else:
        new_situation['score_diff'] = int(-1 * new_situation['score_diff'])

    new_situation['kneel_down'] = kneel_down(new_situation['score_diff'],
                                             new_situation['timd'],
                                             new_situation['secs_left'],
                                             new_situation['dwn'])

    new_situation['qtr_scorediff'] = (
            new_situation['qtr'] * new_situation['score_diff'])

    return new_situation


def field_goal(situation, new_situation, **kwargs):
    new_situation['score_diff'] = situation['score_diff'] + 3

    # Assume the starting field position will be own 25, accounts
    # for touchbacks and some run backs.

    new_situation['yfog'] = 25

    return new_situation


def missed_field_goal(situation, new_situation, **kwargs):
    """Opponent takes over from the spot of the kick."""
    new_situation['yfog'] = 100 - (situation['yfog'] - 8)
    return new_situation


def touchdown(situation, new_situation, **kwargs):
    """Assumes successful XP and no 2PC -- revisit this for 2015?"""
    new_situation['score_diff'] = situation['score_diff'] + 7
    new_situation['yfog'] = 25
    return new_situation


def turnover_downs(situation, new_situation, **kwargs):
    new_situation['yfog'] = 100 - situation['yfog']
    return new_situation


def punt(situation, new_situation, **kwargs):
    """Use the average net punt distance (punt distance - return yards).

    Not all situations have historical data, especially very
    close to opponent's end zone. Use a net punt distance of
    5 yards here.
    """

    default_punt = 5

    try:
        pnet = kwargs['data'].loc[kwargs['data'].yfog == situation['yfog'],
                                  'pnet'].values[0]

    except IndexError:
        pnet = default_punt

    new_yfog = np.floor(100 - (situation['yfog'] + pnet))

    # Touchback
    new_situation['yfog'] = new_yfog if new_yfog > 0 else 25

    return new_situation


def first_down(situation):
    new_situation = OrderedDict()
    new_situation['dwn'] = 1

    yfog = situation['yfog'] + situation['ytg']
    new_situation['ytg'] = min([10, yfog])
    new_situation['yfog'] = yfog

    # 10 seconds of clock time elapsed, or game over.
    new_situation['secs_left'] = max([situation['secs_left'] - 10, 0])

    # These values don't change
    new_situation['score_diff'] = situation['score_diff']
    new_situation['timo'], new_situation['timd'] = (
            situation['timo'], situation['timd'])
    new_situation['spread'] = situation['spread']

    new_situation['kneel_down'] = kneel_down(new_situation['score_diff'],
                                             new_situation['timd'],
                                             new_situation['secs_left'],
                                             new_situation['dwn'])

    new_situation['qtr'] = qtr(new_situation['secs_left'])
    new_situation['qtr_scorediff'] = (
            new_situation['qtr'] * new_situation['score_diff'])

    return new_situation


def qtr(secs_left):
    if secs_left <= 900:
        return 4
    if secs_left <= 1800:
        return 3
    if secs_left <= 2700:
        return 2
    return 1
