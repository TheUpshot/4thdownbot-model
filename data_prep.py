from __future__ import division, print_function

import os

import click
import numpy as np
import pandas as pd


def load_games(game_data_fname, remove_ties=False):
    """Load data containing results of each game and return a DataFrame.

    Parameters
    ----------
    game_data_fname : str, filename of Armchair Analysis GAME table
    remove_ties     : boolean, optional

    Returns
    -------
    games           : DataFrame
    """
    games = pd.read_csv(game_data_fname, index_col='gid')

    # Data from 2000 import is less reliable, omit this season
    # and use regular season games only.

    games = (games.query('seas >= 2001 & week <= 17')
                  .drop(['stad', 'temp', 'humd', 'wspd',
                         'wdir', 'cond', 'surf'],
                        axis='columns'))

    games['winner'] = games.apply(winner, axis=1)
    if remove_ties:
        games = games[games['winner'] != 'TIE']
    return games


def winner(row):
    """Returns the team name that won the game, otherwise returns 'TIE'"""
    if row.ptsv > row.ptsh:
        return row.v
    elif row.ptsh > row.ptsv:
        return row.h
    else:
        return 'TIE'


def load_pbp(pbp_data_fname, games, remove_knees=False):
    """Load the play by play data and return a DataFrame.

    Parameters
    ----------
    pbp_data_fname : str, location of play by play data
    games          : DataFrame, game-level DataFrame created by load_games
    remove_knees   : boolean, optional

    Returns
    -------
    pbp            : DataFrame
    """
    pbp = pd.read_csv(pbp_data_fname, low_memory=False,
                      usecols=['gid', 'pid', 'off', 'def', 'type', 'qtr',
                               'min', 'sec', 'kne', 'ptso', 'ptsd', 'timo',
                               'timd', 'dwn', 'ytg', 'yfog', 'yds', 'fd',
                               'fgxp', 'good', 'pnet', 'pts', 'detail'])

    # Remove overtime
    pbp['qtr'] = pbp['qtr'].astype(np.int32)
    pbp = pbp[pbp.qtr <= 4]

    # pid 183134 should have a value of 0 for min, but has "0:00"
    pbp['min'] = pbp['min'].astype(np.chararray)
    pbp['min'] = pbp['min'].replace({'0:00': 0})
    pbp['min'] = pbp['min'].astype(np.int64)

    # Restrict to regular season games after 2000
    pbp = pbp[pbp.gid.isin(games.index)]

    if remove_knees:
        pbp = pbp[pbp.kne.isnull()]
    return pbp


def switch_offense(df):
    """Swap game state columns for offense & defense dependent variables.
    The play by play data has some statistics on punts and kickoffs in terms
    of the receiving team. Switch these to reflect the game state for
    the kicking team."""

    df.loc[(df['type'] == 'PUNT') | (df['type'] == 'KOFF'),
           ['off', 'def', 'ptso', 'ptsd', 'timo', 'timd']] = df.loc[
                   (df['type'] == 'PUNT') | (df['type'] == 'KOFF'),
                   ['def', 'off', 'ptsd', 'ptso', 'timd', 'timo']].values

    # If any points are scored on a PUNT/KOFF, they are given in terms
    # of the receiving team -- switch this.

    df.loc[(df['type'] == 'PUNT') | (df['type'] == 'KOFF'), 'pts'] = (
            -1 * df.loc[(df['type'] == 'PUNT') | (df['type'] == 'KOFF'),
                        'pts'].values)
    return df


def code_fourth_downs(df):
    """Parse all fourth downs and determine if teams intended to go for it,
    punt, or attempt a field goal. If intent is not clear, do not include
    the play.
    """

    fourths = df.loc[df.dwn.fillna(0).astype(np.int32) == 4, :].copy()
    fourths['goforit'] = np.zeros(fourths.shape[0])
    fourths['punt'] = np.zeros(fourths.shape[0])
    fourths['kick'] = np.zeros(fourths.shape[0])

    # Omit false start, delay of game, encroachment, neutral zone infraction
    # We cannot infer from these plays if the offense was going to
    # go for it or not.

    omitstring = (r'encroachment|false start|delay of game|neutral zone '
                  'infraction')
    fourths = fourths[-(fourths.detail.str.contains(omitstring, case=False))]

    # Ran a play
    fourths.loc[(fourths['type'] == 'RUSH') |
                (fourths['type'] == 'PASS'), 'goforit'] = 1

    fourths.loc[(fourths['type'] == 'RUSH') |
                (fourths['type'] == 'PASS'), 'punt'] = 0

    fourths.loc[(fourths['type'] == 'RUSH') |
                (fourths['type'] == 'PASS'), 'kick'] = 0

    # Field goal attempts and punts
    fourths.loc[(fourths['type'] == 'FGXP') |
                (fourths['type'] == 'PUNT'), 'goforit'] = 0

    fourths.loc[(fourths['type'] == 'FGXP'), 'kick'] = 1
    fourths.loc[(fourths['type'] == 'PUNT'), 'punt'] = 1

    # Punted, but penalty on play
    puntstring = r'punts|out of bounds'
    fourths.loc[(fourths['type'] == 'NOPL') &
                (fourths.detail.str.contains(puntstring, case=False)),
                'punt'] = 1

    # Kicked, but penalty on play
    kickstring = r'field goal is|field goal attempt'
    fourths.loc[(fourths['type'] == 'NOPL') &
                (fourths.detail.str.contains(kickstring, case=False)),
                'kick'] = 1

    # Went for it, but penalty on play
    gostring = (r'pass to|incomplete|sacked|left end|up the middle|'
                'pass interference|right tackle|right guard|right end|'
                'pass intended|left tackle|left guard|pass deep|'
                'pass short|up the middle')

    fourths.loc[(fourths['type'] == 'NOPL') &
                (fourths.detail.str.contains(gostring, case=False)) &
                -(fourths.detail.str.contains(puntstring, case=False)) &
                -(fourths.detail.str.contains(kickstring, case=False)),
                'goforit'] = 1

    fourths = fourths[fourths[['goforit', 'punt', 'kick']].sum(axis=1) == 1]
    return fourths


def fg_success_rate(fg_data_fname, out_fname, min_pid=473957):
    """Historical field goal success rates by field position.

    By default, uses only attempts from >= 2011 season to reflect
    more improved kicker performance. 

    Returns and writes results to a CSV.

    NOTE: These are somewhat sparse and irregular at longer FG ranges.
    This is because kickers who attempt long FGs are not selected at
    random -- they are either in situations which require a long FG
    attempt or are kickers with a known long range. The NYT model
    uses a logistic regression kicking model developed by Josh Katz
    to smooth out these rates.
    """
    fgs = pd.read_csv(fg_data_fname)

    fgs = fgs.loc[(fgs.fgxp == 'FG') & (fgs.pid >= min_pid)].copy()

    fgs_grouped = fgs.groupby('dist')['good'].agg(
            {'N': len, 'average': np.mean}).reset_index()

    fgs_grouped['yfog'] = 100 - (fgs_grouped.dist - 17)
    fgs_grouped[['yfog', 'average']].to_csv(out_fname, index=False)

    return fgs_grouped


def nyt_fg_model(fname, outname):
    """Sub in simple logit for field goal success rates."""
    fgs = pd.read_csv(fname)
    fgs['yfog'] = 100 - (fgs.fg_distance - 17)
    fgs.to_csv(outname)
    return fgs


def punt_averages(punt_data_fname, out_fname, joined):
    """Group punts by kicking field position to get average return distance.
    Currently does not incorporate the possibility of a muffed punt
    or punt returned for a TD.
    """
    
    punts = pd.read_csv(punt_data_fname, index_col='yfog')

    punts = pd.merge(punts, joined[['yfog']],
                     left_index=True, right_index=True)

    punts_dist = pd.DataFrame(punts.groupby('yfog')['pnet']
                                   .mean().reset_index())

    punts_dist.to_csv(out_fname, index=False)
    return punts_dist


def group_coaches_decisions(fourths):
    """Group 4th down decisions by score difference and field
    position to get coarse historical comparisons.

    Writes these to a CSV and returns them."""

    df = fourths.copy()

    df['down_by_td'] = (df.score_diff <= -4).astype(np.uint8)
    df['up_by_td'] = (df.score_diff >= 4).astype(np.uint8)
    df['yfog_bin'] = df.yfog // 20
    df['short'] = (df.ytg <= 3).astype(np.uint8)
    df['med'] = ((df.ytg >= 4) & (df.ytg <= 7)).astype(np.uint8)
    df['long'] = (df.ytg > 7).astype(np.uint8)

    grouped = df.groupby(['down_by_td', 'up_by_td', 'yfog_bin',
                          'short', 'med', 'long'])

    goforit = grouped['goforit'].agg({'proportion_went': np.mean,
                                      'sample_size': len})
    punt = grouped['punt'].agg({'proportion_punted': np.mean,
                                'sample_size': len})
    kick = grouped['kick'].agg({'proportion_kicked': np.mean,
                               'sample_size': len})

    decisions = goforit.merge(
            punt.merge(kick, left_index=True, right_index=True,
                       suffixes=['_punt', '_kick']),
            left_index=True, right_index=True, suffixes=['_goforit', 'punt'])

    decisions.to_csv('data/coaches_decisions.csv')
    return decisions


def first_down_rates(df_plays, yfog):
    """Find the mean 1st down success rate at a given point in the field.

    Parameters
    ----------
    df_plays : DataFrame
    yfog     : str, must be 'yfog' or 'yfog_bin'
               If yfog, use the actual yards from own goal
               If yfog_bin, use the decile of the field instead.
    """

    downs = df_plays.copy()
    downs['first_down'] = downs['first_down'].astype(np.float32)
    if yfog == 'yfog_bin':
        # Break the field into deciles
        downs[yfog] = downs.yfog // 10
        downs = downs.loc[downs.yfog < 90].copy()
    else:
        downs = downs.loc[downs.yfog >= 90].copy()

    # For each segment, find the average first down rate by dwn & ytg
    grouped = (downs.groupby([yfog, 'dwn', 'ytg'])['first_down']
                    .agg({'fdr': np.mean, 'N': len})
                    .reset_index())

    # Just keep 3rd & 4th downs
    grouped = grouped.loc[grouped.dwn >= 3].copy()
    merged = grouped.merge(grouped, on=[yfog, 'ytg'], how='left')

    # Note this will lose scenarios that have *only* ever seen a 4th down
    # This matches to one play since 2001.
    merged = merged.loc[(merged.dwn_x == 4) & (merged.dwn_y == 3)].copy()

    # Compute a weighted mean of FDR on 3rd & 4th down to deal with sparsity
    merged['weighted_N_x'] = (merged.fdr_x * merged.N_x)
    merged['weighted_N_y'] = (merged.fdr_y * merged.N_y)
    merged['weighted_total'] = (merged.weighted_N_x + merged.weighted_N_y)
    merged['total_N'] = (merged.N_x + merged.N_y)
    merged['weighted_fdr'] = (merged.weighted_total / merged.total_N)

    merged = merged.drop(labels=['weighted_N_x', 'weighted_N_y',
                                 'weighted_total', 'total_N'], axis='columns')
    merged = merged.rename(columns={'dwn_x': 'dwn'})

    # Need to fill in any missing combinations where possible
    merged = merged.set_index([yfog, 'dwn', 'ytg'])
    p = pd.MultiIndex.from_product(merged.index.levels,
                                   names=merged.index.names)
    merged = merged.reindex(p, fill_value=None).reset_index()
    merged = merged.rename(columns={'weighted_fdr': 'fdr'})

    # Eliminate impossible combinations
    if yfog == 'yfog_bin':
        # Sparse situations, just set to p(success) = 0.1
        merged.loc[merged.ytg > 13, 'fdr'] = 0.10

        # Missing values inside -10 because no one goes for it here
        merged.loc[(merged.fdr_x.isnull()) & (merged.ytg <= 3),
                   'fdr'] = .2
        merged.loc[(merged.fdr_x.isnull()) & (merged.ytg > 3),
                   'fdr'] = .1

        # Fill in missing values
        merged['fdr'] = merged['fdr'].interpolate()
        merged.to_csv('data/fd_open_field.csv', index=False)
    else:
        merged = merged.loc[(merged.yfog + merged.ytg <= 100)]
        merged.loc[(merged.yfog == 99) & (merged.ytg == 1), 'fdr'] = (
                merged.loc[(merged.yfog == 99) & (merged.ytg == 1), 'fdr_x'])
        merged['fdr'] = merged['fdr'].interpolate()
        merged.to_csv('data/fd_inside_10.csv', index=False)
    return merged


def join_df_first_down_rates(df, fd_open_field, fd_inside_10):
    """Join the computed first down rates with the play by play data."""
    open_field = df.loc[df.yfog < 90].reset_index().copy()
    open_field['yfog_bin'] = open_field.yfog // 10
    open_field = open_field.merge(
            fd_open_field, on=['yfog_bin', 'dwn', 'ytg'], how='left')
    open_field = open_field.drop('yfog_bin', axis='columns')
    inside_10 = df.loc[df.yfog >= 90].reset_index().copy()
    inside_10 = inside_10.merge(
            fd_inside_10, on=['dwn', 'ytg', 'yfog'], how='left')
    new_df = pd.concat([open_field, inside_10]).set_index('pid').sort_index()
    return new_df


def kneel_down(df):
    """Code a situation a 1 if the offense can kneel to end the game
    based on time remaining, defensive timeouts remaining,
    down, and score difference.
    """
    df['kneel_down'] = np.zeros(df.shape[0])

    df.loc[(df.timd == 0) & (df.secs_left <= 120) & (df.dwn == 1) &
           (df.score_diff > 0), 'kneel_down'] = 1
    df.loc[(df.timd == 1) & (df.secs_left <= 84) & (df.dwn == 1) &
           (df.score_diff > 0), 'kneel_down'] = 1
    df.loc[(df.timd == 2) & (df.secs_left <= 48) & (df.dwn == 1) &
           (df.score_diff > 0), 'kneel_down'] = 1

    df.loc[(df.timd == 0) & (df.secs_left <= 84) & (df.dwn == 2) &
           (df.score_diff > 0), 'kneel_down'] = 1
    df.loc[(df.timd == 1) & (df.secs_left <= 45) & (df.dwn == 2) &
           (df.score_diff > 0), 'kneel_down'] = 1

    df.loc[(df.timd == 0) & (df.secs_left <= 42) & (df.dwn == 3) &
           (df.score_diff > 0), 'kneel_down'] = 1

    df.loc[(df.score_diff <= 0) | (df.dwn == 4), 'kneel_down'] = 0
    return df


@click.command()
@click.argument('pbp_data_location')
def main(pbp_data_location):
    pd.set_option('display.max_columns', 200)
    pd.set_option('display.max_colwidth', 200)
    pd.set_option('display.width', 200)

    if not os.path.exists('data'):
        click.echo('Making data directory.')
        os.mkdir('data')

    click.echo('Loading game data.')
    games = load_games('{}/GAME.csv'.format(pbp_data_location))
    click.echo('Loading play by play data.')
    pbp = load_pbp('{}/PBP.csv'.format(pbp_data_location),
                   games, remove_knees=False)

    click.echo('Joining game and play by play data.')
    joined = pbp.merge(games, left_on='gid', right_index=True)

    # Switch offensive and defensive stats on PUNT/KOFF
    click.echo('Munging data...')
    joined = switch_offense(joined)

    # Modify the spread so that the sign is negative when the offense
    # is favored and positive otherwise

    joined['spread'] = joined.sprv
    joined.loc[joined.off != joined.v, 'spread'] = (
            -1.0 * joined.loc[joined.off != joined.v, 'spread'])

    # For model purposes, touchdowns are "first downs" (successful conversion)

    joined['first_down'] = (joined.fd.notnull()) | (joined.pts >= 6)

    # Add winners for classification task
    joined['win'] = (joined.off == joined.winner).astype(np.uint8)

    # Features needed for the win probability model
    joined['score_diff'] = joined.ptso - joined.ptsd
    joined['secs_left'] = (((4 - joined.qtr) * 15.0) * 60 +
                           (joined['min'] * 60) + joined.sec)

    # Group all fourth downs that indicate if the team went for it or not
    # by down, yards to go, and yards from own goal

    click.echo('Processing fourth downs.')
    fourths = code_fourth_downs(joined)

    # Merge the goforit column back into all plays, not just fourth downs
    joined = joined.merge(fourths[['goforit']], left_index=True,
                          right_index=True, how='left')

    click.echo('Grouping and saving historical 4th down decisions.')
    decisions = group_coaches_decisions(fourths)
    fourths_grouped = fourths.groupby(['dwn', 'ytg', 'yfog'])['goforit'].agg(
        {'N': len, 'mean': np.mean})
    fourths_grouped.to_csv('data/fourths_grouped.csv', index=False)

    # Remove kickoffs and extra points, retain FGs
    joined = joined[(joined['type'] != 'KOFF') & (joined.fgxp != 'XP')]

    click.echo('Grouping and saving field goal attempts and punts.')
    fgs_grouped = fg_success_rate('{}/FGXP.csv'.format(pbp_data_location),
                                  'data/fgs_grouped.csv')
    punt_dist = punt_averages('{}/PUNT.csv'.format(pbp_data_location),
                              'data/punts_grouped.csv', joined)

    # Code situations where the offense can take a knee(s) to win
    click.echo('Coding kneel downs.')
    joined = kneel_down(joined)

    click.echo('Computing first down rates.')

    # Only rush & pass plays that were actually executed are eligible
    # for computing first down success rates.

    df_plays = joined.loc[joined['type'].isin(['PASS', 'RUSH']), :].copy()
    fd_open_field = first_down_rates(df_plays, 'yfog_bin')
    fd_inside_10 = first_down_rates(df_plays, 'yfog')
    joined = join_df_first_down_rates(joined, fd_open_field, fd_inside_10)

    joined = joined.loc[joined.dwn<=4,:].copy()
    click.echo('Writing cleaned play-by-play data.')
    joined.to_csv('data/pbp_cleaned.csv')

if __name__ == '__main__':
    main()
