#########################################
##### Name: Jessica Wu              #####
##### Uniqname: jlwu                #####
##### Final Project                 #####
#########################################

import requests
import json
import geopy.distance
import random


GEOCODING_KEY = 'pk.eyJ1IjoiamVzc2ljYWx3dSIsImEiOiJjbGdhMmJjYmIwdXAxM2VwOTNzNzhsZmxjIn0.pyd1X8CXQBA-_Djhbd-0iw'
GEOCODING_BASE_URL = 'https://api.mapbox.com/geocoding/v5/mapbox.places/'
CITYBIKE_BASE_URL = 'http://api.citybik.es/v2/networks/'
NETWORKS_CACHE_FILENAME = 'networks_cache.json'


def main():
    # creating list of bike networks if not yet cached
    networks_cache = open_cache(NETWORKS_CACHE_FILENAME)
    if networks_cache == {}:
        bike_networks = create_json(CITYBIKE_BASE_URL)['networks']
        save_cache(bike_networks, NETWORKS_CACHE_FILENAME)
    else:
        bike_networks = networks_cache

    # creating a list of cities with bike share systems from bike_networks
    bike_cities = [network['location']['city'].lower() for network in bike_networks]

    # checking to see if there is a bike share system in user's city -- maybe turn into separate function
    city = input('Please enter your current city: ')
    found_network = 'no'
    for place in bike_cities:
        if city.lower() in place:
            found_network = 'yes'
            idx = bike_cities.index(place)
            network_name = bike_networks[idx]['name']
            print(f"Yay! There is a bike-share system near you, called {network_name}!")
            break
    if found_network == 'no': #remember to loop back to start of program if no network found
        print('Sorry, there is no bike-share system in your city yet.')

    network_id = bike_networks[idx]['id']
    stations = create_json(CITYBIKE_BASE_URL + network_id)['network']['stations']

    # #make sure to create way to deal with no results (AKA, create_coord_json returns None)
    address = input('Please enter your current address: ')
    current_coord = create_coordinates_json(address)

    # telling user closest station. could make separate function
    lowest_distance = calculate_distance((stations[0]['latitude'], stations[0]['longitude']), current_coord)
    closest_stn = stations[0]
    for station in stations:
        if station['free_bikes'] > 0:
            stn_coord = (station['latitude'], station['longitude'])
            distance = calculate_distance(stn_coord, current_coord)
            if distance < lowest_distance:
                lowest_distance = distance
                closest_stn = station

    print(f"The closest station to you is {closest_stn['name']}.\nThis station is {round(lowest_distance, 2)}km away.\nThere are currently {closest_stn['free_bikes']} free bikes.")

    # ask user for bike route length range
    desired_length = float(input('Please enter how long (in km) you would like your bike route to be: '))
    stns_in_range = []
    for station in stations:
        rt_length = calculate_distance((station['latitude'], station['longitude']), current_coord)
        if rt_length <= desired_length + 0.2 and rt_length >= desired_length - 0.2 and station['empty_slots'] > 0:
            stns_in_range.append([station, rt_length])
    # if stns in range empty, ask user to input another range

    # suggest end station (create tree with stations in range) -- suggest another if user not satisfied
    rando = random.choice(stns_in_range)
    print(f"I suggest you bike to the {rando[0]['name']} station, which is {round(rando[1], 2)}km away.")

    # suggest POI near end station and generate google maps
    coord_search = str(rando[0]['longitude']) +', '+ str(rando[0]['latitude'])
    coord_url = GEOCODING_BASE_URL + coord_search + '.json?types=poi&limit=1&access_token=' + GEOCODING_KEY
    poi = create_json(coord_url)['features'][0]
    poi_name = poi['place_name']
    poi_type = poi['properties']['category']

    print(f"You should also check out {poi_name}, which is by your endpoint! It's a super cool {poi_type}!")

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

if __name__ == '__main__':
    main()