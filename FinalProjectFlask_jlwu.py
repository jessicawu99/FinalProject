#########################################
##### Name: Jessica Wu              #####
##### Uniqname: jlwu                #####
##### Final Project                 #####
#########################################

# Note to grader!
# To test different cities, here is a list of cities with bike-share systems:
# https://en.wikipedia.org/wiki/List_of_bicycle-sharing_systems
# I most often used cities such as Philadelphia, New York, and Paris to test my application. Enjoy!

import requests
import json
import geopy.distance
from flask import Flask, render_template, request

app = Flask(__name__)

GEOCODING_KEY = 'pk.eyJ1IjoiamVzc2ljYWx3dSIsImEiOiJjbGdhMmJjYmIwdXAxM2VwOTNzNzhsZmxjIn0.pyd1X8CXQBA-_Djhbd-0iw'
GEOCODING_BASE_URL = 'https://api.mapbox.com/geocoding/v5/mapbox.places/'
CITYBIKE_BASE_URL = 'http://api.citybik.es/v2/networks/'
NETWORKS_CACHE_FILENAME = 'networks_cache.json'
TREE = []

def open_cache(cache_filename):
    ''' opens the cache file if it exists and loads the JSON into
    the dictionary.
    if the cache file doesn't exist, creates a new cache dictionary

    Parameters
    ----------
    None
    Returns
    -------
    The opened cache
    '''
    try:
        cache_file = open(cache_filename, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict

def save_cache(cache_dict, cache_filename):
    ''' saves the current state of the cache to disk
    Parameters
    ----------
    cache_dict: dict
    The dictionary to save
    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(cache_filename,"w")
    fw.write(dumped_json_cache)
    fw.close()

def create_json(url):
    resp = requests.get(url)
    results_object = resp.json()
    return results_object

def create_coordinates_json(address):
    '''
    creates a json object from an address search using Geocoding API
    Parameters
    ----------
    address: string
        user's current address
    Returns
    -------
    list
        coordinates representing inputted address
    '''
    search_url = GEOCODING_BASE_URL + address + '.json?access_token=' + GEOCODING_KEY
    resp = requests.get(search_url)
    results_object = resp.json()
    if results_object['features'] == []:
        return None
    coord = results_object['features'][0]['geometry']['coordinates']
    coord.reverse()
    return coord

def calculate_distance(coord1, coord2):
    return geopy.distance.geodesic(coord1, coord2).km

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/createroute', methods=['POST'])
def create_route():
    city = request.form['city']
    address = request.form['address']
    desired_length = request.form['desired_length']

    if not city or not address or not desired_length:
        return render_template('moreinfo.html')

    try:
        desired_length = float(desired_length)
    except:
        return render_template('moreinfo.html')


    for place in bike_cities:
        if city.lower() in place:
            idx = bike_cities.index(place)
            network_name = bike_networks[idx]['name']
            # found network, now getting id and creating stations list
            network_id = bike_networks[idx]['id']
            stations = create_json(CITYBIKE_BASE_URL + network_id)['network']['stations']

            current_coord = create_coordinates_json(address)

            # telling user closest station
            lowest_distance = calculate_distance((stations[0]['latitude'], stations[0]['longitude']), current_coord)
            closest_stn = stations[0]
            for station in stations:
                if station['free_bikes'] > 0:
                    stn_coord = (station['latitude'], station['longitude'])
                    distance = calculate_distance(stn_coord, current_coord)
                    if distance < lowest_distance:
                        lowest_distance = distance
                        closest_stn = station

            # create list of stations in range
            stns_in_range = []
            for station in stations:
                rt_length = calculate_distance((station['latitude'], station['longitude']), current_coord)
                if rt_length <= desired_length + 0.2 and rt_length >= desired_length - 0.2 and station['empty_slots'] > 0:
                    stns_in_range.append([station, rt_length])

            # if no stations near desired range
            if stns_in_range == []:
                return render_template('noendpoint.html',
                                   networkname = network_name,
                                   closeststn = closest_stn,
                                   lowestdistance = round(lowest_distance, 2))

            # suggest end station
            choice = stns_in_range[0]

            # suggest POI near end station and generate google maps
            coord_search = str(choice[0]['longitude']) +', '+ str(choice[0]['latitude'])
            coord_url = GEOCODING_BASE_URL + coord_search + '.json?types=poi&limit=1&access_token=' + GEOCODING_KEY
            poi = create_json(coord_url)['features'][0]
            poi_name = poi['place_name']
            poi_type = poi.get('properties').get('category')

            origin_coord = str(closest_stn['latitude']) +', '+ str(closest_stn['longitude'])
            dest_coord = str(choice[0]['latitude']) +', '+ str(choice[0]['longitude'])
            gmaps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin_coord}&destination={dest_coord}&travelmode=bicycling"

            more_stns = []
            for station in stations:
                rt_length = calculate_distance((station['latitude'], station['longitude']), current_coord)
                if rt_length <= desired_length + 1.5 and rt_length >= desired_length + 0.5 and station['empty_slots'] > 0:
                    more_stns.append([station, rt_length])
            if len(more_stns) > 1 and len(stns_in_range) > 2:
                TREE.append(address)
                TREE.append([
                        [str(desired_length), [stns_in_range[1][0]['name'], stns_in_range[2][0]['name']]],
                        [str(desired_length + 1), [more_stns[0][0]['name'], more_stns[1][0]['name']]]
                    ])


            return render_template('makeroute.html',
                                   networkname = network_name,
                                   closeststn = closest_stn,
                                   lowestdistance = round(lowest_distance, 2),
                                   stns_in_range = stns_in_range,
                                   choice = choice,
                                   choice_distance = round(choice[1], 2),
                                   poi_name = poi_name,
                                   poi_type = poi_type,
                                   gmaps_url = gmaps_url,
                                   tree = TREE)

    # if no networks found
    return render_template('nonetwork.html')


@app.route('/viewroutes', methods=['POST'])
def view_route():
    selected = request.form.getlist('newlength')
    similar_checked = "similar" in selected
    longer_checked = "longer" in selected

    return render_template('seeroutes.html', tree=TREE, similar_checked=similar_checked, longer_checked=longer_checked)

if __name__ == '__main__':
    # creating list of bike networks if not yet cached
    networks_cache = open_cache(NETWORKS_CACHE_FILENAME)
    if networks_cache == {}:
        bike_networks = create_json(CITYBIKE_BASE_URL)['networks']
        save_cache(bike_networks, NETWORKS_CACHE_FILENAME)
    else:
        bike_networks = networks_cache

    # creating a list of cities with bike share systems from bike_networks
    bike_cities = [network['location']['city'].lower() for network in bike_networks]

    print('starting Flask app', app.name)
    app.run(debug=True)