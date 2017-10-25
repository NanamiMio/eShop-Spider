#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re

import requests
import xmltodict
import pycountry

GET_GAMES_US_URL = "http://www.nintendo.com/json/content/get/filter/game?system=switch&sort=title&direction=asc&shop=ncom"
GET_GAMES_EU_URL = "http://search.nintendo-europe.com/en/select"
GET_GAMES_JP_CURRENT = "https://www.nintendo.co.jp/data/software/xml-system/switch-onsale.xml"
GET_GAMES_JP_COMING = "https://www.nintendo.co.jp/data/software/xml-system/switch-coming.xml"
GET_GAMES_JP_ALT = "https://www.nintendo.co.jp/api/search/title?category=products&pf=switch&q=*&count=25"
GUESS_GAMES_GP_URL = 'https://ec.nintendo.com/JP/ja/titles/'
GET_PRICE_URL = "https://api.ec.nintendo.com/v1/price?lang=en"

GAME_LIST_LIMIT = 200
PRICE_LIST_LIMIT = 50

GAME_CODE_REGEX_JP = r'\/HAC(\w{4})'
GAME_CODE_REGEX_US = r'HAC\w(\w{4})'
GAME_CODE_REGEX_EU = r'HAC\w(\w{4})'

NSUID_REGEX_JP = r'\d{14}'
JSON_REGEX = r'NXSTORE\.titleDetail\.jsonData = ([^;]+);'

GAME_CHECK_CODE_US = 70010000000185
GAME_CHECK_CODE_EU = 70010000000184
GAME_CHECK_CODE_JP = 70010000000039

REGION_ASIA = "CN HK AE AZ HK IN JP KR MY SA SG TR TW".split(' ')
REGION_EUROPE = "AD AL AT AU BA BE BG BW CH CY CZ DE DJ DK EE ER ES FI FR GB GG GI GR HR HU IE IM IS IT JE LI LS LT LU LV MC ME MK ML MR MT MZ NA NE NL NO NZ PL PT RO RS RU SD SE SI SK SM SO SZ TD VA ZA ZM ZW".split(' ')
REGION_AMERICA = "AG AI AR AW BB BM BO BR BS BZ CA CL CO CR DM DO EC GD GF GP GT GY HN HT JM KN KY LC MQ MS MX NI PA PE PY SR SV TC TT US UY VC VE VG VI".split(' ')

COUNTRIES = "AT AU BE BG CA CH CY CZ DE DK EE ES FI FR GB GR HR HU IE IT JP LT LU LV MT MX NL NO NZ PL PT RO RU SE SI SK US ZA".split(' ')

FIRST_NSUID = 70010000000026

def getGamesAmerica(offset = 0, games=[]):
    #print(offset, len(games))
    params = {'offset':offset, 'limit':GAME_LIST_LIMIT}
    r = requests.get(GET_GAMES_US_URL, params=params)
    result = json.loads(r.text)

    total = result['filter']['total']
    getGames = result['games']['game']
    #print(total, len(getgames))

    games = unique(games, getGames, 'slug')

    if(len(getGames) + offset < total):
        return getGamesAmerica(offset + GAME_LIST_LIMIT, games)

    return games

def getGamesJapan():
    r = requests.get(GET_GAMES_JP_CURRENT)
    r.encoding = 'utf-8'
    gamesCurrent = xmltodict.parse(r.text)['TitleInfoList']['TitleInfo']
    

    r = requests.get(GET_GAMES_JP_COMING)
    r.encoding = 'utf-8'
    gamesComing = xmltodict.parse(r.text)['TitleInfoList']['TitleInfo']
    
    gamesCurrent.extend(gamesComing)
    return gamesCurrent

def guessGamesJapan():
    games = []
    for i in range(FIRST_NSUID, FIRST_NSUID + 1500):
        r = requests.get(GUESS_GAMES_GP_URL + str(i))
        if r.status_code is 200:
            game = json.loads(re.search(JSON_REGEX, r.text).group(1))
            games.append(game)
            print(i, r.status_code)
        # else:
        #     print(i, r.status_code)

    return games



def getGamesEurope():   
    params = {
        'fl': 'product_code_txt,title,date_from,nsuid_txt,image_url_sq_s',
        'fq': 'type:GAME AND system_type:nintendoswitch* AND product_code_txt:*',
        'q': '*',
        'rows': 9999,
        'sort': 'sorting_title asc',
        'start': 0,
        'wt': 'json',
    }

    r = requests.get(GET_GAMES_EU_URL, params=params)
   
    result = json.loads(r.text)['response']
    print(result['numFound'], len(result['docs']))

    return result['docs']


def unique(games, addgames, key):
    keyset = set()
    
    for game in addgames:
        if game[key] not in keyset:
            keyset.add(game[key])
            games.append(game)
    
    return games

def getShopsByCountryCodes(countryCodes, gamecode, region):
    shops=[]

    for code in countryCodes:
        r = getPrices(code, [gamecode,])
        if 'error' not in r:
            print(code, 'Success')
            shop = {
                'code': code,
                'country': pycountry.countries.get(alpha_2=code).name,
               # 'currency': r['prices'][0]['regular_price']['currency'],
                'region' : region
            }
            shops.append(shop)
        else:
            print(code, 'Fail')
    
    return shops

def getShopsAsia():
    return getShopsByCountryCodes(REGION_ASIA, GAME_CHECK_CODE_JP, 'Asia')

def getShopsEurope():
    return getShopsByCountryCodes(REGION_EUROPE, GAME_CHECK_CODE_EU, 'Europe')

def getShopsAmerica():
    return getShopsByCountryCodes(REGION_AMERICA, GAME_CHECK_CODE_US, 'America')

def getShops():
    shops=[]
    shops.extend(getShopsAsia())
    shops.extend(getShopsEurope())
    shops.extend(getShopsAmerica())
    return shops

def getPrices(country, gameIds, offset = 0, prices = []):
    # print(gameIds)
    filteredIds = gameIds[offset: offset + PRICE_LIST_LIMIT]
    # print(filteredIds)
    params = {
        'country' : country,
        'limit' : PRICE_LIST_LIMIT,
        'ids' : filteredIds
    }
    # print(params)
    r = requests.get(GET_PRICE_URL, params)
    result = json.loads(r.text)
    return r.text

    if('error' in result):
        response = {"error" : result["error"]}
        return response

    if ('prices' not in result):
        response = {"error" : "No prices"}
        return response

    prices.extend(result['prices'])

    if(len(result['prices']) + offset < len(gameIds)):
        return getPrices(country, gameIds, offset + PRICE_LIST_LIMIT, prices)
    
    response = {
        'personalized': False,
        'country': 'US',
        'prices': prices
    }
    return response

def parseGameCode(game, region):

    code = ""

    if region is "Europe" and 'product_code_txt' in game:
        code = re.match(GAME_CODE_REGEX_EU, game['product_code_txt'][0]).group(1)
    if region is "Asia" and 'ScreenshotImgURL' in game:
        code = re.match(GAME_CODE_REGEX_JP, game['ScreenshotImgURL'][0]).group(1)
    if region is "America" and 'game_code' in game:
        code = re.match(GAME_CODE_REGEX_US, game['game_code']).group(1)

    return code


def parseNSUID(game, region):

    nsuid = ""

    if region is "Europe" and 'nsuid_txt' in game:
        nsuid = game['nsuid_txt']
    if region is "Asia" and 'LinkURL' in game:
        nsuid = re.match(NSUID_REGEX_JP, game['LinkURL'][0]).group(1)
    if region is "America" and 'nsuid' in game:
        nsuid =  game['nsuid']

    return nsuid
        


if __name__=='__main__':
    result = guessGamesJapan()
    print(result[0], len(result))
    # with open('result.json', 'w') as f:
        # f.write(result)