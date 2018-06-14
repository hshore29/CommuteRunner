AGENCY_MAPPING = {
    None: 'Unknown',
    "Amtrak": 'Amtrak',
    "Bee-Line Bus": 'Other Bus',
    "Bieber Tourways": 'Charter Bus',
    "Coach USA - Suburban Trails Inc": 'Charter Bus',
    "CTTransit - Meriden": 'Other Bus',
    "CTTransit - Waterbury": 'Other Bus',
    "CTTransit- New Haven": 'Other Bus',
    "CTTransit- Stamford": 'Other Bus',
    "Express Bus Service": 'Other Bus', # Route 4 Jitney
    "Greater Bridgeport Transit": 'Other Bus',
    "Greyhound": 'Charter Bus',
    "Lakeland Bus": 'Charter Bus',
    "LANTA": 'Other Bus',
    "Long Island Rail Road": 'LIRR',
    "Metro-North Railroad": 'Metro-North',
    "Middlesex County Area Transit": 'Other Bus',
    "MTA Bus Company": 'MTA Bus',
    "MTA New York City Transit": 'Subway',
    "Nassau Inter-County Express": 'Other Bus',
    "NJ TRANSIT BUS": 'NJ Transit Bus',
    "NJ TRANSIT RAIL": 'NJ Transit',
    "Norwalk Transit District": 'Other Bus',
    "NY Waterway": 'Ferry',
    "OurBus": 'Charter Bus',
    "Peter Pan Bonanza Division": 'Charter Bus',
    "Peter Pan Bus Lines": 'Charter Bus',
    "Port Authority Trans-Hudson Corporation": 'PATH',
    "Seastreak": 'Ferry',
    "SEPTA": 'SEPTA',
    "Somerset County": 'Other Bus',
    "Sussex County Skylands Ride": 'Other Bus',
    "Ulster County Area Transit": 'Other Bus',
    }

AGENCY_COLORS = {
    'Unknown': '#000',
    'Amtrak': '#1B3F67',
    'Charter Bus': '#666',
    'LIRR': '#0039A6',
    'MTA Bus': '#0039A6',
    'Metro-North': '#0039A6',
    'NJ Transit': '#2C4885',
    'NJ Transit Bus': '#A32684',
    #'NJ Transit Alt': '#E86C34',
    'Subway': '#0039A6',
    'Other Bus': '#999',
    'Ferry': '#6FBBEE',
    'PATH': '#2366AC',
    'SEPTA': '#E34528',
    }

LINE_COLORS = {
    'NJ Transit': {
        # https://en.wikipedia.org/wiki/NJ_Transit_Rail_Operations#Lines
        # https://en.wikipedia.org/wiki/Hudson–Bergen_Light_Rail
        'Atlantic City Line': '#005DAA',
        'Gladstone Branch': '#A2D5AE',
        'Main/Bergen County Line': '#FFCF01', # Main Line
        'Montclair-Boonton Line': '#E66B5B',
        'Morris & Essex Line': '#00A94F',
        'North Jersey Coast Line': '#00A4E4',
        'Northeast Corridor': '#EF3E42',
        'Pascack Valley Line': '#8E258D',
        'Raritan Valley Line': '#FAA634',
        'Port Jervis Line': '#FF7900', # Metro-North
        'Hudson-Bergen Light Rail': '#FFDD00', # Also '#008C4E', '#009EDA'
        'Newark Light Rail': '#504682', # From logo colors
        'Riverline Light Rail': '#3B97C4', # From NJT Schedule
        },
    }

MODE_COLORS = {
    'FERRY': '#6FBBEE',
    'HEAVY_RAIL': '#1B3F67',
    'TRAM': '#0039A6',
    'BUS': '#A32684',
    'SUBWAY': '#0039A6',
    'WALKING': '#AAA',
    'DRIVING': '#666',
    }

KEEP_LINES = ["LIRR", "Metro-North", "Subway", "NJ Transit", "PATH"]
LOW_DETAIL = ["Bieber Tourways", "Greyhound", "OurBus"]
