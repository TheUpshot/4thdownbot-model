
import nfldb
import pandas as pd
import re

minyear = 2009
maxyear = 2014

def play_to_type(p):

    if p.rushing_att>0:
        ptype = 'RUSH'
    elif p.passing_att>0:
        ptype = 'PASS'
    elif p.punting_yds>0:
        ptype = 'PUNT'
    elif p.kicking_fga>0:
        ptype = 'FGXP'
    elif p.kicking_xpa>0:
        ptype = 'FGXP'
    elif p.kicking_tot>0:
        ptype = 'KOFF'
    else:
        ptype = None
    return ptype

def pbp_keys():
    ks = ['gid', 'pid', 'off', 'def', 'type', 'qtr',
          'min', 'sec', 'kne', 'ptso', 'ptsd', 'timo',
          'timd', 'dwn', 'ytg', 'yfog', 'yds', 'fd',
          'fgxp', 'good', 'pnet', 'pts', 'detail']

    return ks

def elapsed_to_min_sec(elapsed):
    t = 900-elapsed
    minute = int(t)/int(60)
    sec = t-minute*60
    return minute, sec

def full_team_to_abbr(team_name):
    for t in nfldb.team.teams:
        v = t[0]
        for x in t[0:]:
            if team_name in x:
                return v
    return None

def timeout_team_id(description):
    m = re.search('#([1-9])\s+by\s+([A-Z]+)', description )
    if m:
        return m.group(2), m.group(1)

    m = re.search('\.\s+([A-Za-z\s]+)\s+[c|C]hallenged.+Timeout\s+#([1-9])', description )
    if m:
        abbr = full_team_to_abbr(m.group(1))
        return abbr, m.group(2)

    # special exception
    # 2012093011
    #(:20) (Shotgun) R.Griffin pass deep right to N.Paul to
    # TB 37 for 30 yards (B.McDonald; A.Black). 10 lateral to 16,
    # 16 lateraled back to 10  Tampa Bay challenged the illegal
    # forward pass ruling, and the play was Upheld. (Timeout #2.)

    m = re.search('[0-9]+\s+([A-Za-z\s]+)\s+challenged.+Timeout\s+#([1-9])', description )
    if m:
        abbr = full_team_to_abbr(m.group(1))
        return abbr, m.group(2)

    # special exception
    # 2012120910
    # (14:19) R.Tannehill pass short right to D.Bess to
    # MIA 33 for 8 yards (N.Bowman). Caught at MIA 33.  0-yds YAC San Francisco challenged
    # the pass completion ruling, and the play was Upheld. (Timeout #3 at 14:00.)

    m = re.search('YAC\s+([A-Za-z\s]+)\s+challenged.+Timeout\s+#([1-9])', description )
    if m:
        abbr = full_team_to_abbr(m.group(1))
        return abbr, m.group(2)

    # special exception
    # 2010091203
    # (2:02)  Indianapolis challenged the incomplete
    # pass ruling, and the play was Upheld. (Timeout #1.)

    m = re.search('\)\s+([A-Za-z\s]+)\s+challenged.+Timeout\s+#([1-9])', description )
    if m:
        abbr = full_team_to_abbr(m.group(1))
        return abbr, m.group(2)

    #  special exception
    # ??
    if ' J.Powers ran ob at NYG 44 for 33 yards. PENALTY on NYG-B.Jacobs, Unnece' in description:
        return 'IND', 0

    # special exception
    # (12:48) M.Sanu pass deep right to
    # G.Bernard pushed ob at CLE 9 for 25 yards (B.Mingo).
    # {Ball lateraled from Dalton to Sanu} Cleveland challenged the
    # pass completion ruling, and the play was Upheld. (Timeout #2.)
    if 'Ball lateraled from Dalton to Sanu' in description:
        return 'CLE', 2

    # special exception
    #  (14:32) (No Huddle, Shotgun) N.Foles scrambles up the
    # middle to PHI 31 for 1 yard (P.Willis). Measurement
    # for 1st Down San Francisco challenged the first down ruling, and the play...

    m = re.search('own\s+([A-Za-z\s]+)\s+challenged.+Timeout\s+#([1-9])', description )
    if m:
        abbr = full_team_to_abbr(m.group(1))
        return abbr, m.group(2)

    #special exception
    # 2014100600 (12:10) (Shotgun) R.Wilson pass short right to L.Willson
    #  to WAS 32 for 19 yards (D.Amerson, R.Clark). 3-Wilson's full
    # body did not cross the line
    # scrimage before
    # throwing the ball Washington challenged the illegal
    # forward pass ruling, and the play was Upheld.
    # The ruling on the field was confirmed. (Timeout #1.) None
    m = re.search('ball\s+([A-Za-z\s]+)\s+challenged.+Timeout\s+#([1-9])', description )
    if m:
        abbr = full_team_to_abbr(m.group(1))
        return abbr, m.group(2)

    # special exception
    # 2010101005 *** play under review ***
    if '*** play under review ***' == description:
        return 'XXX', 0

    return None


def play_to_nyt_format(g, p, score):
    h = g.home_team
    a = g.away_team
    ks = pbp_keys()
    tmp = {}
    tmp['gid'] = p.gsis_id
    tmp['pid'] = '%s%04d%05d' % (str(p.gsis_id), int(p.drive_id), int(p.play_id))
    tmp['off'] = p.pos_team
    tmp['def'] = h if a == p.pos_team else a
    tmp['type'] = play_to_type(p)
    game_phase = p.time.phase.name
    m = re.search('Q([1-4])', game_phase)
    if m:
        qtr = int(m.group(1))
        minute, sec = elapsed_to_min_sec(p.time.elapsed)
    else:
        qtr = 999
        minute, sec = 0, 0
    tmp['qtr'] = qtr
    tmp['min'] = minute
    tmp['sec'] = sec
    tmp['yds'] = p.offense_yds

    ptsh, ptsa = score[:]

    if p.pos_team == h:
        tmp['ptso'] = ptsh
        tmp['ptsd'] = ptsa
    elif p.pos_team == a:
        tmp['ptso'] = ptsa
        tmp['ptsd'] = ptsh
    else:
        tmp['ptso'] = None
        tmp['ptsd'] = None

    tmp['kne'] = 0
    tmp['good'] = p.kicking_fgm + p.kicking_xpmade
    tmp['ytg'] = p.yards_to_go
    if p.yardline._offset is not None:
        tmp['yfog'] = p.yardline._offset + 50
    else:
        tmp['yfog'] = None

    if p.kicking_fga>0:
        tmp['fgxp'] = 'FG'
    elif p.kicking_xpa>0:
        tmp['fgxp'] = 'XP'
    else:
        tmp['fgxp'] = ''

    tmp['pnet'] = p.kicking_yds - p.kickret_yds

    tmp['dwn'] = p.down
    tmp['pts'] = p.points
    if p.scoring_team == tmp['def']:
        tmp['pts'] *= -1

    tmp['detail'] = p.description.replace(',', '')

    tmp['fd'] = 1 if p.first_down==1 else None
    return tmp

def make_punts(db, ofile='nfldb_data/PUNT.csv'):
    q = nfldb.Query(db)
    q.game(season_year__ge=minyear, season_year__le=maxyear, season_type='Regular')
    q.play_player(punting_tot__ge=1)

    data = {}
    ks = ['pnet', 'yfog']

    for k in ks:
        data[k] = []

    punts = q.as_plays()
    for p in punts:
        tmp = {}
        tmp['pnet'] = float(p.punting_yds) - float(p.puntret_yds)
        tmp['yfog'] = int(p.yardline._offset) + 50

        for k in ks:
            data[k].append(tmp[k])

    df = pd.DataFrame(data)
    df.to_csv(ofile)

def make_fgxp(db, ofile='nfldb_data/FGXP.csv'):
    q = nfldb.Query(db)
    q.game(season_year__ge=minyear, season_year__le=maxyear, season_type='Regular')
    q.play_player(kicking_fga=1)

    data = {}
    ks = ['dist', 'fgxp', 'pid', 'good']
    for k in ks:
        data[k] = []

    fgas = q.as_play_players()
    for fga in fgas:
        tmp = {}
        tmp['pid'] = 999999999
        tmp['fgxp'] = 'FG'
        if fga.kicking_fgm==1:
            tmp['dist'] = fga.kicking_fgm_yds
            tmp['good'] = 1
        elif fga.kicking_fgmissed==1:
            tmp['dist'] = fga.kicking_fgmissed_yds
            tmp['good'] = 0
        else:
            raise Exception
        for k in ks:
            data[k].append(tmp[k])

    df = pd.DataFrame(data)
    df.to_csv(ofile)


def make_pbp(db, ofile='nfldb_data/PBP.csv'):
    '''

    :param db:
    :param ofile:
    :return:
    dwn,yfog,secs_left,score_diff,timo,timd,spread,kneel_down,qtr,type,win
    '''

    q = nfldb.Query(db)
    q.game(season_year__ge=minyear, season_year__le=maxyear, season_type='Regular')
    games = q.as_games()
    data = {}
    for k in pbp_keys():
        data[k] = []

    ng = len(games)
    for ig, g in enumerate(games):
        score = [0,0]
        timeout_cache = {}
        if ig%20 == 0:
            print 'game', ig, ' of ', ng
        plays = g.plays
        for iplay, p in enumerate(plays):
            nyt = play_to_nyt_format(g, p, score)
            off_team = nyt['off']
            def_team = nyt['def']
            for team_abbr in [off_team, def_team]:
            # set initialvalues for timeout cache
                if not team_abbr in timeout_cache:
                    timeout_cache[team_abbr] = 0


            if p.timeout==1:
                team_abbr, timeout_number = timeout_team_id(p.description)
                tn = int(timeout_number)
                if tn>3:
                    # it can happen from injuries
                    # e.g. 2012111811 Timeout #4 by PIT at 00:22.
                    # Injury. No penalty for fourth timeout.
                    tn = 3
                timeout_cache[team_abbr] = tn

            nyt['timo'] = 3-timeout_cache[off_team]
            nyt['timd'] = 3-timeout_cache[def_team]

            for k in nyt:
                data[k].append(nyt[k])

            play_score = g.score_in_plays([plays[iplay]])
            score[0] += play_score[0]
            score[1] += play_score[1]

    for k in data:
        print k, len(data[k])

    df = pd.DataFrame(data)
    df.to_csv(ofile)

def make_games(db, ofile='nfldb_data/GAME.csv'):
    '''
    :param db:
    :param ofile:
    :return:

    gid, seas, week, ptsh, ptsv, spread
    '''

    q = nfldb.Query(db)
    q.game(season_year=2012, season_type='Regular')
    games = q.as_games()

    dummy_keys = ['stad', 'temp', 'humd', 'wspd', 'wdir', 'cond', 'surf']
    ks = {'gid':'gsis_id', 'seas': None,
          'week': 'week',
          'ptsh': 'home_score',
          'ptsv': 'away_score',
          'sprv': None,
          'h': None, 'v': None
          }
    data = {}
    for k in ks:
        data[k] = []

    for k in dummy_keys:
        data[k] = []

    for g in games:
        tmp = {}
        tmp['gid'] = g.gsis_id
        tmp['week'] = g.week
        tmp['ptsh'] = g.home_score
        tmp['ptsv'] = g.away_score
        tmp['sprv'] = 0
        tmp['seas'] = g.season_year

        tmp['h'] = g.home_team
        tmp['v'] = g.away_team
        for k in tmp:
            data[k].append(tmp[k])

        for k in dummy_keys:
            data[k].append('')

    df = pd.DataFrame(data)
    df.to_csv(ofile)

if __name__=='__main__':
    db = nfldb.connect()
    make_games(db)
    make_pbp(db)
    make_fgxp(db)
    make_punts(db)
