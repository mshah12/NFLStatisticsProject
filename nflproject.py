# USES STANDARD SCORING #
import time
import json
import base64
import requests
import http.client
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import consts as const

def getPlayerID():
    print("Enter player's first and last name (seperated by a space): ", end='')
    first_last_name = str(input()).split(" ")
    print('')
    cleaned_name = [first_last_name[i].capitalize() for i in range(0, len(first_last_name))]
    Ocp_Apim_Key = {'Ocp-Apim-Subscription-Key' : 'db36c6f99f854e6aa5c0b3ba9f8ebb46'}
    teams = json.loads(json.dumps((requests.get('https://api.sportsdata.io/v3/nfl/scores/json/Teams', headers=Ocp_Apim_Key).json())))
    active_teams = []
    for team in teams:
        roster_json = requests.get('https://api.sportsdata.io/v3/nfl/scores/json/Players/' + team['Key'], headers=Ocp_Apim_Key)
        roster = json.loads(json.dumps(roster_json.json()))
        for player in roster:
            if player['FirstName'] == cleaned_name[0] and player['LastName'] == cleaned_name[1]:
                return player['SportRadarPlayerID']

def getPlayerStats():
    consumer_key = 'stkg937egzbsaa97bjbdygcr'
    conn = http.client.HTTPSConnection("api.sportradar.us")
    conn.request("GET", "/nfl/official/trial/v5/en/players/" + getPlayerID() + "/profile.json?api_key=" + consumer_key)
    stats_byte = conn.getresponse().read()
    player_stats = dict(json.loads(stats_byte.decode('utf-8')))
    return player_stats

def getSeasonStats(playerSeason, playerStats):
    position =  playerStats['position']
    for season in playerStats['seasons']:
        if season['year'] == playerSeason:
            games_played = season['teams'][0]['statistics']['games_played']
            if position == 'QB':
                try:
                    rushingStats = calculateRushingStats(season['teams'][0]['statistics']['rushing'], season['teams'][0]['statistics']['fumbles'], games_played)
                except:
                    rushingStats = 0
                try:
                    passingStats = calculatePassingStats(season['teams'][0]['statistics']['passing'], games_played)
                except:
                    passingStats = 0
                kickingStats, receivingStats = 0, 0
            elif position == 'RB':
                try:
                    rushingStats = calculateRushingStats(season['teams'][0]['statistics']['rushing'], season['teams'][0]['statistics']['fumbles'], games_played)
                except:
                    rushingStats = 0
                try:
                    receivingStats = calculateReceivingStats(season['teams'][0]['statistics']['receiving'], games_played)
                except:
                    receivingStats = 0
                passingStats, kickingStats = 0, 0
            elif position == 'WR':
                try:
                    rushingStats = calculateRushingStats(season['teams'][0]['statistics']['rushing'], season['teams'][0]['statistics']['fumbles'], games_played)
                except:
                    rushingStats = 0
                try:
                    receivingStats = calculateReceivingStats(season['teams'][0]['statistics']['receiving'], games_played)
                except:
                    receivingStats = 0
                passingStats, kickingStats = 0, 0
            elif position == 'K':
                try:
                    kickingStats = calculateKickingStats(season['teams'][0]['statistics'], games_played)
                except:
                    kickingStats = 0
                rushingStats, passingStats, receingStats = 0, 0, 0
            season_stats = np.array([rushingStats + passingStats + kickingStats + receivingStats]).sum()
            return season_stats

def calculatePassingStats(passingStats, gamesPlayed):
    pstats = [passingStats['completions'] / gamesPlayed * passingStats['avg_yards'] * const.POINTS_PER_QBYD,
              passingStats['touchdowns'] / gamesPlayed * const.POINTS_PER_TD,
              passingStats['interceptions'] / gamesPlayed * const.POINTS_PER_INTERCEPTION]
    projected_pstats = np.array(pstats).sum()
    return projected_pstats

def calculateRushingStats(rushingStats, fumbleStats, gamesPlayed):
    rfstats = [rushingStats['attempts'] / gamesPlayed * rushingStats['avg_yards'] * const.POINTS_PER_YD,
              rushingStats['touchdowns'] / gamesPlayed * const.POINTS_PER_TD]
    rfstats.append(fumbleStats['lost_fumbles'] / gamesPlayed * const.POINTS_PER_FUMBLELOST)
    projected_rfstats = np.array(rfstats).sum()
    return projected_rfstats

def calculateReceivingStats(receivingStats, gamesPlayed):
    rstats = [receivingStats['receptions'] / gamesPlayed * receivingStats['avg_yards'] * const.POINTS_PER_YD,
              receivingStats['touchdowns'] / gamesPlayed * const.POINTS_PER_TD]
    projected_rstats = np.array(rstats).sum()
    return projected_rstats

def calculateKickingStats(kickingStats, gamesPlayed):
    avg_kick = np.floor(kickingStats['field_goals']['avg_yards'])
    if avg_kick < 40:
        avg_ppfg = const.POINTS_PER_30YDFG
    elif avg_kick < 50:
        avg_ppfg = const.POINTS_PER_40YDFG
    elif avg_kick < 60:
        avg_ppfg = const.POINTS_PER_50YDFG
    elif avg_kick >= 60:
        avg_ppfg = const.POINTS_PER_60YDFG
    kstats = [kickingStats['field_goals']['made'] / gamesPlayed * avg_ppfg,
              (kickingStats['field_goals']['attempts'] - kickingStats['field_goals']['made']) / gamesPlayed * const.POINTS_PER_MISSEDFG,
              kickingStats['extra_points']['made'] / gamesPlayed * const.POINTS_PER_XP,
              (kickingStats['extra_points']['attempts'] - kickingStats['extra_points']['made']) / gamesPlayed * const.POINTS_PER_MISSEDFG]
    projected_kstats = np.array(kstats).sum()
    return projected_kstats

def projectedStats():
    Ocp_Apim_Key = {'Ocp-Apim-Subscription-Key' : 'db36c6f99f854e6aa5c0b3ba9f8ebb46'}
    curr_season = json.loads(json.dumps((requests.get('https://api.sportsdata.io/v3/nfl/scores/json/CurrentSeason', headers=Ocp_Apim_Key).json())))
    return getSeasonStats(curr_season, getPlayerStats())

def getPastSeasons(playerStats):
    position =  playerStats['position']
    past_seasons = {}
    for season in playerStats['seasons']:
        past_seasons[season['year']] = getSeasonStats(season['year'], playerStats)
    return past_seasons

def simpleGraph(pastSeasons):
    years = np.array(list(seasonYear for seasonYear in pastSeasons.keys()))
    scores = np.array(list(seasonScore for seasonScore in pastSeasons.values()))
    fig, axes = plt.subplots(nrows=1, ncols=1)
    plots = axes.plot(scores)
    axes.grid(True)
    axes.set_xlabel('Year')
    axes.set_ylabel('Average Fantasy Points Scored')
    fig.suptitle('Average Fantasy Points over Career')
    ticks = np.linspace(years[0], years[len(years) - 1], years[len(years) - 1])
    axes.set_xticks(ticks)
    fig.show()

def pipeline():
    start_time = time.time()
    print('Projected Stat: ' + str(projectedStats()) + ' points')
    print('')
    print("(in " + str(time.time() - start_time) + " seconds)")

print((projectedStats()))
