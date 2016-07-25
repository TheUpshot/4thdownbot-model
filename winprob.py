from __future__ import division, print_function

import logging
import random
import sys

from sklearn.utils.validation import NotFittedError

from collections import OrderedDict

import plays as p


logging.basicConfig(stream=sys.stderr)


def generate_response(situation, data, model):
    """Parent function called by the bot to make decisions on 4th downs.

    Parameters
    ----------
    situation : OrderedDict
    data      : dict, contains historical data
    model     : LogisticRegression

    Returns
    -------
    payload   : dict
    """

    situation = calculate_features(situation, data)

    # Generate the game state of possible outcomes
    scenarios = simulate_scenarios(situation, data)

    # Calculate the win probability for each scenario
    probs = generate_win_probabilities(situation, scenarios, model, data)

    # Calculate breakeven points, make decision on optimal decision
    decision, probs = generate_decision(situation, data, probs)

    payload = {'decision': decision, 'probs': probs, 'situation': situation}

    return payload


def calculate_features(situation, data):
    """Generate features needed for the win probability model that are
    not contained in the general game state information passed via API.

    Parameters
    ----------
    situation : OrderedDict

    Returns
    -------
    situation : The same OrderedDict, with new keys and values.
    """

    situation['kneel_down'] = p.kneel_down(situation['score_diff'],
                                           situation['timd'],
                                           situation['secs_left'],
                                           situation['dwn'])

    situation['qtr'] = qtr(situation['secs_left'])
    situation['qtr_scorediff'] = situation['qtr'] * situation['score_diff']

    situation['spread'] = (
            situation['spread'] * (situation['secs_left'] / 3600))

    cum_pct = (
        (situation['secs_left'] - data['final_drives'].secs).abs().argmin())

    situation['poss_prob'] = data['final_drives'].ix[cum_pct].cum_pct

    return situation


def qtr(secs_left):
    """Given the seconds left in the game, determine the current quarter."""
    if secs_left <= 900:
        return 4
    if secs_left <= 1800:
        return 3
    if secs_left <= 2700:
        return 2
    return 1


def simulate_scenarios(situation, data):
    """Simulate game state after each possible outcome.

    Possible scenarios are: touchdown, first down, turnover on downs,
    field goal attempt (success or failure), and punt.
    """

    features = data['features']
    scenarios = dict()

    # If it's 4th & goal, success is a touchdown, otherwise a 1st down.

    if situation['ytg'] + situation['yfog'] >= 100:
        scenarios['touchdown'] = p.change_poss(situation, p.touchdown, features)
    else:
        scenarios['first_down'] = p.first_down(situation)

    scenarios['fail'] = p.change_poss(situation, p.turnover_downs, features)

    scenarios['punt'] = p.change_poss(situation, p.punt, features,
                                      data=data['punts'])

    scenarios['fg'] = p.change_poss(situation, p.field_goal, features)
    scenarios['missed_fg'] = p.change_poss(situation, p.missed_field_goal,
                                           features)

    return scenarios


def generate_win_probabilities(situation, scenarios, model, data, **kwargs):
    """For each of the possible scenarios, estimate the win probability
    for that game state."""

    probs = dict.fromkeys([k + '_wp' for k in scenarios.keys()])

    features = data['features']

    # Pre-play win probability calculation
    # Note there is more information in situation than just model features.

    feature_vec = [val for key, val in situation.items() if key in features]
    try:
        feature_vec = data['scaler'].transform(feature_vec)
    except NotFittedError:
        raise Exception("Sklearn reports that the instance is not yet fitted. " + 
                        "This usually means that the version of python used to train " +
                        "the model is different from the version you are currently running.")

    probs['pre_play_wp'] = model.predict_proba(feature_vec)[0][1]

    for scenario, outcome in scenarios.items():
        feature_vec = [val for key, val in outcome.items() if key in features]
        feature_vec = data['scaler'].transform(feature_vec)
        pred_prob = model.predict_proba(feature_vec)[0][1]

        # Change of possessions require 1 - WP
        if scenario in ('fg', 'fail', 'punt', 'missed_fg', 'touchdown'):
            pred_prob = 1 - pred_prob

        probs[str(scenario + '_wp')] = pred_prob

    # Account for situations in which an opponent's field goal can end
    # the game, driving win probability down to 0.

    if (situation['secs_left'] < 40 and (0 <= situation['score_diff'] <= 2)
            and situation['timo'] == 0):
        # Estimate probability of successful field goal and
        # set the win probability of failing to convert a 4th down
        # to that win probability.

        if situation['dome'] > 0:
            prob_opp_fg = (data['fgs'].loc[
                    data['fgs'].yfog == scenarios['fail']['yfog'],
                    'dome_rate'].values[0])
        else:
            prob_opp_fg = (data['fgs'].loc[
                    data['fgs'].yfog == scenarios['fail']['yfog'],
                    'open_rate'].values[0])

        probs['fail_wp'] = ((1 - prob_opp_fg) * probs['fail_wp'])

    # Teams may not get the ball back during the 4th quarter

    if situation['qtr'] == 4:
        probs['fail_wp'] = probs['fail_wp'] * situation['poss_prob']
        probs['punt_wp'] = probs['punt_wp'] * situation['poss_prob']

    # Always have a 'success_wp' field, regardless of TD or 1st down

    if 'touchdown_wp' in probs:
        probs['success_wp'] = probs['touchdown_wp']
    else:
        probs['success_wp'] = probs['first_down_wp']
    return probs


def generate_decision(situation, data, probs, **kwargs):
    """Decide on optimal play based on game states and their associated
    win probabilities. Note the currently 'best play' is based purely
    on the outcome with the highest expected win probability. This
    does not account for uncertainty of these estimates.

    For example, the win probabilty added by a certain play may be
    very small (0.0001), but that may be the 'best play.'
    """

    decision = {}

    decision['prob_success'] = calc_prob_success(situation, data)

    # Expected value of win probability of going for it
    wp_ev_goforit = expected_win_prob(decision['prob_success'],
                                      probs['success_wp'],
                                      probs['fail_wp'])
    probs['wp_ev_goforit'] = wp_ev_goforit

    # Expected value of kick factors in probability of FG
    probs['prob_success_fg'], probs['fg_ev_wp'] = expected_wp_fg(
            situation, probs, data)

    # If the offense can end the game with a field goal, set the
    # expected win probability for a field goal attempt to the
    # probability of a successful field goal kick.

    if (situation['secs_left'] < 40 and (-2 <= situation['score_diff'] <= 0)
        and situation['timd'] == 0):
            probs['fg_wp'] = probs['prob_success_fg']
            probs['fg_ev_wp'] = probs['prob_success_fg']

    # If down by more than a field goal in the 4th quarter, need to
    # incorporate the probability that you will get the ball back.

    if situation['qtr'] == 4 and situation['score_diff'] < -3:
        probs['fg_ev_wp'] = probs['fg_ev_wp'] * situation['poss_prob']

    # Breakeven success probabilities
    decision['breakeven_punt'], decision['breakeven_fg'] = breakeven(probs)

    # Of the kicking options, pick the one with the highest E(WP)
    decision['kicking_option'], decision['wpa_going_for_it'] = (
            best_kicking_option(probs, wp_ev_goforit))

    # Make the final call on kick / punt / go for it
    # If a win is unlikely in any circumstance, favor going for it.

    # if probs['pre_play_wp'] < .05:
    #     decision['best_play'] = 'go for it'
    # else:
    decision['best_play'] = decide_best_play(decision)

    # Only provide historical data outside of two-minute warning
    decision = get_historical_decision(situation, data, decision)

    return decision, probs


def get_historical_decision(situation, data, decision):
    """Compare current game situation to historically similar situations.

    Currently uses score difference and field position to provide
    rough guides to what coaches have done in the past.
    """

    historical_data = data['decisions']

    down_by_td = situation['score_diff'] <= -4
    up_by_td = situation['score_diff'] >= 4
    yfog_bin = situation['yfog'] // 20
    short_tg = int(situation['ytg'] <= 3)
    med_tg = int((situation['ytg'] >= 4) and (situation['ytg'] <= 7))
    long_tg = int(situation['ytg'] > 7)

    history = historical_data.loc[(historical_data.down_by_td == down_by_td) &
                                  (historical_data.up_by_td == up_by_td) &
                                  (historical_data.yfog_bin == yfog_bin) &
                                  (historical_data.short == short_tg) &
                                  (historical_data.med == med_tg) &
                                  (historical_data['long'] == long_tg)]

    # Check to see if no similar situations
    if historical_data.shape[0] == 0:
        decision['historical_goforit_pct'] = 'None'
        decision['historical_punt_pct'] = 'None'
        decision['historical_kick_pct'] = 'None'
        decision['historical_N'] = 'None'
    else:
        decision['historical_punt_pct'] = (history.proportion_punted.values[0])
        decision['historical_kick_pct'] = (history.proportion_kicked.values[0])
        decision['historical_goforit_pct'] = (history.proportion_went.values[0])
        decision['historical_goforit_N'] = (history.sample_size.values[0])
    return decision


def expected_win_prob(pos_prob, pos_win_prob, neg_win_prob):
    """Expected value of win probability, factoring in p(success)."""
    return (pos_prob * pos_win_prob) + ((1 - pos_prob) * neg_win_prob)


def expected_wp_fg(situation, probs, data):
    """Expected WP from kicking, factoring in p(FG made)."""
    if 'fg_make_prob' in situation and isinstance(situation['fg_make_prob'], float):
        pos = situation['fg_make_prob']
    else:
        fgs = data['fgs']

        # Set the probability of success of implausibly long kicks to 0.
        if situation['yfog'] < 42:
            pos = 0
        else:
            # Account for indoor vs. outdoor kicking
            if situation['dome'] > 0:
                pos = fgs.loc[fgs.yfog == situation['yfog'], 'dome_rate'].values[0]
            else:
                pos = fgs.loc[fgs.yfog == situation['yfog'], 'open_rate'].values[0]

    return pos, expected_win_prob(pos, probs['fg_wp'], probs['missed_fg_wp'])
    return pos, expected_win_prob(pos, probs['fg_wp'], probs['missed_fg_wp'])


def breakeven(probs):
    """Calculates the breakeven point for making the decision.

    The breakeven is the point at which a coach should be indifferent
    between two options. We compare the expected win probability
    of going for it on 4th down to the next best kicking option
    and determine what the probability of converting the 4th down
    needs to be in order to make the coach indifferent to going for it
    or kicking.
    """

    denom = probs['success_wp'] - probs['fail_wp']

    breakeven_punt = (probs['punt_wp'] - probs['fail_wp']) / denom
    breakeven_fg = (probs['fg_ev_wp'] - probs['fail_wp']) / denom

    # Coerce breakevens to be in the range [0, 1]
    breakeven_punt = max(min(1, breakeven_punt), 0)
    breakeven_fg = max(min(1, breakeven_fg), 0)

    return breakeven_punt, breakeven_fg


def calc_prob_success(situation, data):
    """Use historical first down rates. When inside the opponent's 10,
    use dwn, ytg, yfog specific rates. Otherwise, use binned yfog where
    field is broken into 10 segments"""

    fd_open = data['fd_open_field']
    fd_inside = data['fd_inside_10']

    if situation['yfog'] < 90:
        try:
            yfog_bin = situation['yfog'] // 10
            p_success = fd_open.loc[(fd_open.dwn == situation['dwn']) &
                                    (fd_open.ytg == situation['ytg']) &
                                    (fd_open.yfog_bin == yfog_bin),
                                    'fdr'].values[0]
        except IndexError:
            # Arbitrary, set the probability of success for very long
            # 4th downs to be 0.1
            p_success = 0.1

    else:
        p_success = fd_inside.loc[(fd_inside.dwn == situation['dwn']) &
                                  (fd_inside.ytg == situation['ytg']) &
                                  (fd_inside.yfog == situation['yfog']),
                                  'fdr'].values[0]
    return p_success


def best_kicking_option(probs, wp_ev_goforit):
    """Use the expected win probabilities to determine best kicking option"""

    # Account for end of game situations where FG WP is higher
    if probs['fg_ev_wp'] > probs['punt_wp'] and probs['prob_success_fg'] > .3:
        decision = 'kick'
        win_prob_added = wp_ev_goforit - probs['fg_ev_wp']

    else:
        decision = 'punt'
        win_prob_added = wp_ev_goforit - probs['punt_wp']

    return decision, win_prob_added


def decide_best_play(decision):
    if (decision['kicking_option'] == 'punt' and
            decision['prob_success'] < decision['breakeven_punt']):
        return 'punt'

    elif (decision['kicking_option'] == 'kick' and
            decision['prob_success'] < decision['breakeven_fg']):
        return 'kick'

    else:
        return 'go for it'


def random_play(data):
    """Generate a random play with plausible values for debugging purposes."""

    features = data['features']
    situation = OrderedDict.fromkeys(features)

    situation['dwn'] = 4
    situation['ytg'] = random.randint(1, 10)
    situation['yfog'] = random.randint(1, (100 - situation['ytg']))
    situation['secs_left'] = random.randint(1, 3600)
    situation['score_diff'] = random.randint(-20, 20)
    situation['timo'] = random.randint(0, 3)
    situation['timd'] = random.randint(0, 3)
    situation['spread'] = 0

    situation = calculate_features(situation, data)

    situation['dome'] = random.randint(0, 1)
    return situation
