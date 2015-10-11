from __future__ import division, print_function

import os

import click
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.cross_validation import train_test_split
from sklearn.externals import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (auc, classification_report,
                             f1_score, log_loss, roc_curve)
from sklearn.preprocessing import StandardScaler


def calibration_plot(preds, truth):
    """Produces a calibration plot for the win probability model.

    Splits the predictions into percentiles and calculates the
    percentage of predictions per percentile that were wins. A perfectly
    calibrated model means that plays with a win probability of n%
    win about n% of the time.
    """
    cal_df = pd.DataFrame({'pred': preds, 'win': truth})
    cal_df['pred_bin'] = pd.cut(cal_df.pred, 100, labels=False)

    win_means = cal_df.groupby('pred_bin')['win'].mean()

    plt.figure()
    plt.plot(win_means.index.values,
             [100 * v for v in win_means.values], color='SteelBlue')
    plt.plot(np.arange(0, 100), np.arange(0, 100), 'k--', alpha=0.3)
    plt.xlim([0.0, 100])
    plt.ylim([0.0, 100])
    plt.xlabel('Estimated win probability')
    plt.ylabel('True win percentage')
    plt.title('Win probability calibration, binned by percent')
    plt.show()

    return


def plot_roc(fpr, tpr, roc_auc):
    """Plots the ROC curve for the win probability model along with
    the AUC.
    """
    fig, ax = plt.subplots()
    ax.set(title='Receiver Operating Characteristic',
           xlim=[0, 1], ylim=[0, 1], xlabel='False Positive Rate',
           ylabel='True Positive Rate')
    ax.plot(fpr, tpr, 'b', label='AUC = %0.2f' % roc_auc)
    ax.plot([0, 1], [0, 1], 'k--')
    ax.legend(loc='lower right')
    plt.show()


@click.command()
@click.option('--plot/--no-plot', default=False)
def main(plot):
    pd.set_option('display.max_columns', 200)

    # Only train on actual plays, remove 2pt conversion attempts
    click.echo('Reading play by play data.')
    df = pd.read_csv('data/pbp_cleaned.csv', index_col=0)
    df_plays = df.loc[(df['type'] != 'CONV')].copy()

    # Custom features
    # Interaction between qtr & score difference -- late score differences
    # are more important than early ones.
    df_plays['qtr_scorediff'] = df_plays.qtr * df_plays.score_diff

    # Decay effect of spread over course of game
    df_plays['spread'] = df_plays.spread * (df_plays.secs_left / 3600)

    # Features to use in the model
    features = ['dwn', 'yfog', 'secs_left',
                'score_diff', 'timo', 'timd', 'spread',
                'kneel_down', 'qtr',
                'qtr_scorediff']
    target = 'win'

    click.echo('Splitting data into train/test sets.')
    (train_X, test_X, train_y, test_y) = train_test_split(df_plays[features],
                                                          df_plays[target],
                                                          test_size=0.1)

    click.echo('Scaling features.')
    scaler = StandardScaler()
    scaler.fit(train_X)
    train_X_scaled = scaler.transform(train_X)

    click.echo('Training model.')
    logit = LogisticRegression()
    logit.fit(train_X_scaled, train_y)

    click.echo('Making predictions on test set.')
    test_X_scaled = scaler.transform(test_X)
    preds = logit.predict_proba(test_X_scaled)[:, 1]

    click.echo('Evaluating model performance.')
    fpr, tpr, thresholds = roc_curve(test_y, preds)
    roc_auc = auc(fpr, tpr)
    click.echo('AUC: {}'.format(roc_auc))
    click.echo('Log loss: {}'.format(log_loss(test_y, preds)))

    pred_outcomes = logit.predict(test_X_scaled)
    click.echo(classification_report(test_y, pred_outcomes))
    click.echo('F1 score: {}'.format(f1_score(test_y, pred_outcomes)))

    if plot:
        click.echo('Plotting ROC curve and calibration plot.')
        click.echo('Note: plots may appear behind current active window.')
        plot_roc(fpr, tpr, roc_auc)
        calibration_plot(preds, test_y)

    click.echo('Pickling model and scaler.')
    if not os.path.exists('models'):
        os.mkdir('models')

    joblib.dump(logit, 'models/win_probability.pkl')
    joblib.dump(scaler, 'models/scaler.pkl')

if __name__ == '__main__':
    main()
