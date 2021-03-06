import random
import requests
from .Models.Filter import Filter
from .Models.Location import Location
from .Models.user import User
from .Models.Feedback import Feedback
from .extensions import bcrypt
from .extensions import mongo
from .googlemapAPI import durationCalculation
from .googlemapAPI import timeCalculator
from .googlemapAPI import parsingLocationSygic
from .googlemapAPI import TimeItineraryFactory
from .googlemapAPI import parsingLocation
from .googlemapAPI import crawlLocationsSygic
from .googlemapAPI import crawlLocations
from .googlemapAPI import validateLocation
from flask import Blueprint, request, jsonify
import os
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))

main = Blueprint('main', __name__)


@main.route('/test')
def test():
    user_collection = mongo.db.users
    user_collection.insert({'email': 'random'})
    resp = jsonify(success=True)
    return resp


def CheckIfUserExists(email):
    user_collection = mongo.db.users
    user = user_collection.find_one({"email": email})
    return user


@main.route('/signup', methods=['GET', 'POST'])
def SignUp():
    return_message = "Success"
    content = request.get_json(silent=True)
    email = content.get('email')
    password = content.get('password')
    user = User(email, password)
    try:
        user.createAccount()
    except ValueError:
        return_message = "Password Does Not Exist"
    resp = jsonify(success=return_message)
    return resp


@main.route('/signin', methods=['GET', 'POST'])
def SignIn():
    return_message = "Success"
    content = request.get_json(silent=True)
    email = content.get('email')
    password = content.get('password')
    user = User(email, password)
    try:
        if(user.checkIfUserExists() == None):
            return_message = "User Does Not Exist"
    except ValueError:
        return_message = "Password Does Not Exist"
    resp = jsonify(success=return_message)
    return resp


@main.route('/enterLocation', methods=['GET', 'POST'])
def verifyLocation():
    return_message = "Success"
    content = request.get_json(silent=True)
    email = content.get('email')
    inputLocation = content.get('location')
    backendResponse = validateLocation(inputLocation)
    if(backendResponse == None):
        return_message = "Location Does Not Exist"
    else:
        address = backendResponse[0]
        latitude = backendResponse[1]['lat']
        longitude = backendResponse[1]['lng']
        location = Location(inputLocation, address, latitude, longitude)
        location.insert(email)
    resp = jsonify(success=return_message)
    return resp


@main.route('/addPref', methods=['GET', 'POST'])
def addPreference():
    return_message = "Success"
    content = request.get_json(silent=True)
    email = content.get('email')
    preference = content.get('preference')
    user = CheckIfUserExists(email)
    user_preference = user.get('preference')
    if user_preference is None:
        pref_list = [preference]
        mongo.db.users.update_one(
            {'email': email}, {'$set': {'preference': pref_list}})
    else:
        # check if the preference already exist in the list
        if preference not in user_preference:
            user_preference.append(preference)
        mongo.db.users.update_one(
            {'email': email}, {'$set': {'preference': user_preference}})
    return return_message
        
@main.route('/deletePref', methods=['DELETE','POST'])
def deletePreference():
    return_message = "Success"
    content = request.get_json(silent=True)
    email = content.get('email')
    del_pre = content.get('delpreference')
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print(del_pre)
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    user = CheckIfUserExists(email)
    user_pre = user.get('preference')
    if user_pre is not None:
        if del_pre in user_pre:
            user_pre.remove(del_pre)
        mongo.db.users.update_one(
            {'email': email}, {'$set': {'preference': user_pre}})
    return return_message


@main.route('/getPref', methods=['GET', 'POST'])
def getPreference():
    content = request.get_json(silent=True)
    email = content.get('email')
    print('before getting user')
    user = CheckIfUserExists(email)
    print('after getting user')
    result = user.get('preference')
    if result is None:
        result = []
    resp = jsonify(result)
    return resp


@main.route('/popularlist', methods=['GET', 'POST'])
def popularlist():
    # getting the popular lactivities in user's location and preference
    content = request.get_json(silent=True)
    # user inputs
    email = content.get('email')
    user = CheckIfUserExists(email)
    trip_filter = user.get("filter")
    if user != None:
        # starting location, parsing into coordinate
        location = user.get('location')
        coordinate = str(location.get('lat')) + ", " + str(location.get('lng'))
        # list of possible preferences
        preference_list = user.get('preference')
        # check the max activity numbers wanted
        max_act = int(user.get('filter').get('activity_num'))
        print(max_act)

        # all the locations that fits the requirement
        result_locations = crawlLocations(
            coordinate, preference_list, trip_filter)
        # list store the duplicating place
        duplicate = []
        nameList = []
        for i in result_locations:
            if i['name'] not in nameList:
                nameList.append(i['name'])
            else:
                duplicate.append(i)
        # remove the duplicating elements in result_location
        for j in duplicate:
            result_locations.remove(j)
        # use the limitation of max activity numbers to chop the list
        if (max_act is None):
            return_list = nameList
        else:
            return_list = nameList[:max_act]
        mongo.db.users.update_one(
            {'email': email}, {'$set': {'history_search': result_locations}})
        resp = jsonify(return_list)
    else:
        resp = None
    return resp

@main.route('/getAPIList', methods=['GET','POST'])
def getAPIList():
    # call generateItinery to get list from api
    generateItinerary()
    # get the name of list
    '''
    result = []
    for i in APIlist:
        result.append(i.get("name"))
    resp = jsonify(result)
    return resp
    '''
    return getNameList()
   


@main.route('/getname', methods=['GET','POST'])
def getNameList():
    content = request.get_json(silent = True)
    # user inputs, get user from the input of the user
    pressed = content.get('pressed')
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print(pressed)
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    email = content.get('email')
    user = CheckIfUserExists(email)
    if pressed:  
        if user is not None:
            # if the user is not none, get the itinerary list in the user
            itinerarylist = user.get("itinerary")
            result = []
            # if the user does not have itinerary list, result is empty list
            if itinerarylist is not None:
                # else, result is all the name in itinerary list
                for i in itinerarylist:
                    result.append(i.get('name'))
            resp = jsonify(result)
            
    else:
        resp = jsonify([])
    return resp


@main.route('/getDetail', methods=['GET', 'POST'])
def get_detail():
    # get 'name' and 'email' contents of input
    content = request.get_json(silent=True)
    email = content.get('email')
    place_name = content.get('name')
    # get the user using email
    user = CheckIfUserExists(email)
    result = {}
    if user is not None:
        # get the search history of the user
        search_history = user.get('itinerary')
        if search_history is not None:
            for i in search_history:
                if i['name'] == place_name:
                    result['vicinity'] = i.get('vicinity')
                    result['photos'] = i.get('photo')
                    format_start_time = i.get('startTimeTrip').split()[0] +"T"+i.get('startTimeTrip').split()[1]+":00-05:30"
                    format_end_time = i.get('endTimeTrip').split()[0] +"T"+i.get('endTimeTrip').split()[1]+":00-05:30"
                    print(format_start_time,format_end_time)
                    result['start_time'] = format_start_time
                    result['end_time'] = format_end_time
        else:
            result = None
    else:
        result = None
    resp = jsonify(result)
    return resp

@main.route('/generateItinerary', methods=['POST', 'GET'])
def generateItinerary():
    # getting the popular lactivities in user's location and preference
    content = request.get_json(silent=True)
    # user inputs
    email = content.get('email')
    user = CheckIfUserExists(email)
    trip_filter = user.get("filter")
    if user != None:
        # starting location, parsing into coordinate
        location = user.get('location')
        coordinate = str(location.get('lat')) + "," + str(location.get('lng'))
        # get the start and end date from frontend
        start = user.get('filter').get('StartDateAndTime')
        end = user.get('filter').get('EndingDateAndTime')
        # list of possible preferences
        preference_list = user.get('preference')
        # check the max activity numbers wanted
        max_act = user.get('filter').get('activity_num')
        print(max_act)
        # all the locations that fits the requirement
        result_locations, result_locations_sub = crawlLocationsSygic(coordinate, preference_list, trip_filter, max_act)
        # extract the information we want, change the unreasonable time duration and stored opening hours
        print(result_locations)
        parsed_list = parsingLocationSygic(result_locations, start, end)
        print(parsed_list)
        # generate an Itinerary with time attributes
        itinerary = TimeItineraryFactory(parsed_list, start, end)
        mongo.db.users.update_one(
            {'email': email}, {'$set': {'itinerary': itinerary}})
        mongo.db.users.update_one(
            {'email': email}, {'$set': {'choice_itinerary': result_locations_sub}})
        resp = jsonify(itinerary)
    else:
        resp = None
    return resp


@main.route('/addFilter', methods=['GET', 'POST'])
def addFilter():
    return_message = "Success"
    content = request.get_json(silent=True)
    email = content.get('email')
    content_filters = content.get('filter')

    filters = Filter(email)
    filters.addFilters(content_filters)

    return return_message


@main.route('/getFilter', methods=['GET', 'POST'])
def getFilter():
    content = request.get_json(silent=True)
    print(content)
    email = content.get('email')

    filters = Filter(email)
    return filters.getFilters()

@main.route('/addFeedback', methods=['GET', 'POST'])
def addFeedback():
    return_message = "Success"

    content = request.get_json(silent=True)
    email = content.get('email')
    rating = content.get('rating')
    comment = content.get('comment')

    feedback = Feedback(email, rating, comment)
    feedback.addFeedback()

    return return_message

@main.route('/getLatLong', methods=['GET', 'POST'])
def getLatAndLong():
    content = request.get_json(silent=True)
    location = content.get('vicinity')
    print(location)
    backendResponse = validateLocation(location)
    print(backendResponse)
    latitude = backendResponse[1]['lat']
    longitude = backendResponse[1]['lng']
    addressList = {"latitude": latitude, "longitude": longitude}
    resp = jsonify(addressList)
    return resp
