#!/usr/bin/env python3
"""Comic inventory: strip name -> provider slug.

Extracted from the dosage plugin definitions that used to drive fetches
(dosagelib.plugins.gocomics / .comicskingdom). Keep in sync with the
Comics/<Provider>/<Name>/ directories that harvest.py walks.
"""

COMICSKINGDOM = {
    "Bizarro": "bizarro",
    "HagarTheHorrible": "hagar-the-horrible",
    "Mutts": "mutts",
    "PardonMyPlanet": "pardon-my-planet",
    "RhymesWithOrange": "rhymes-with-orange",
    "SallyForth": "sally-forth",
    "Zits": "zits",
}

GOCOMICS = {
    "AdamAtHome": "adamathome",
    "BabyBlues": "babyblues",
    "CalvinAndHobbes": "calvinandhobbes",
    "DaddysHome": "daddyshome",
    "Doonesbury": "doonesbury",
    "ForBetterOrForWorse": "forbetterorforworse",
    "FrankAndErnest": "frank-and-ernest",
    "Garfield": "garfield",
    "GetFuzzy": "getfuzzy",
    "JumpStart": "jumpstart",
    "Luann": "luann",
    "NonSequitur": "nonsequitur",
    "Overboard": "overboard",
    "PearlsBeforeSwine": "pearlsbeforeswine",
    "Pickles": "pickles",
    "RoseIsRose": "roseisrose",
    "ShermansLagoon": "shermanslagoon",
    "TheDuplex": "duplex",
    "WallaceTheBrave": "wallace-the-brave",
    "WizardOfId": "wizardofid",
}

# GoComics mirror on arcamax.com (plain HTML, no bot wall). Only the strips it
# actually carries: the other 7 have no arcamax page.
ARCAMAX = {
    "BabyBlues": "babyblues",
    "DaddysHome": "daddyshome",
    "Doonesbury": "doonesbury",
    "ForBetterOrForWorse": "forbetterorforworse",
    "Garfield": "garfield",
    "GetFuzzy": "getfuzzy",
    "Luann": "luann",
    "NonSequitur": "nonsequitur",
    "PearlsBeforeSwine": "pearlsbeforeswine",
    "Pickles": "pickles",
    "RoseIsRose": "roseisrose",
    "WallaceTheBrave": "wallacethebrave",
    "WizardOfId": "wizardofid",
}
# GoComics strips with no arcamax equivalent: AdamAtHome, CalvinAndHobbes,
# FrankAndErnest, JumpStart, Overboard, ShermansLagoon, TheDuplex.

EXPECTED_STRIPS = len(COMICSKINGDOM) + len(GOCOMICS)  # 27
