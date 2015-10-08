from collections import OrderedDict

import click
import pandas as pd

from sklearn.externals import joblib

import winprob as wp


def load_data():
    click.echo('Loading data and setting up model.')
    data = {}

    try:
        data['fgs'] = pd.read_csv('data/fgs_grouped_nyt.csv')
    except IOError:
        data['fgs'] = pd.read_csv('data/fgs_grouped.csv')
    data['punts'] = pd.read_csv('data/punts_grouped.csv')
    data['fd_open_field'] = pd.read_csv('data/fd_open_field.csv')
    data['fd_inside_10'] = pd.read_csv('data/fd_inside_10.csv')
    data['decisions'] = pd.read_csv('data/coaches_decisions.csv')
    data['scaler'] = joblib.load('models/scaler.pkl')
    data['features'] = ['dwn', 'yfog', 'secs_left',
                        'score_diff', 'timo', 'timd', 'spread',
                        'kneel_down', 'qtr', 'qtr_scorediff']

    model = joblib.load('models/win_probability.pkl')
    return data, model


@click.command()
def run_bot():
    click.echo("\n\n*** Hit CTRL-C to leave the program. *** \n\n")
    while True:
        situation = OrderedDict.fromkeys(data['features'])
        situation['dwn'] = int(raw_input('Down: '))
        situation['ytg'] = int(raw_input('Yards to go: '))
        situation['yfog'] = int(raw_input('Yards from own goal: '))
        situation['secs_left'] = int(raw_input('Seconds remaining in game: '))
        situation['score_diff'] = int(raw_input("Offense's lead (can be "
                                                "negative): "))
        situation['timo'] = int(raw_input("Timeouts remaining, offense: "))
        situation['timd'] = int(raw_input("Timeouts remaining, defense: "))
        situation['spread'] = float(raw_input("Spread in terms of offensive "
                                              "team (can be negative, enter "
                                              "0 if you don't know): "))
        situation['dome'] = int(raw_input('Is game in dome? 1 for yes, '
                                          '0 for no. '))

        response = wp.generate_response(situation, data, model)

        click.echo(response)

if __name__ == '__main__':
    data, model = load_data()
    run_bot()
