import streamlit as st
from google.cloud import firestore
import googlemaps
import folium
import numpy as np
from streamlit_folium import st_folium, folium_static

import json
from google.oauth2 import service_account

# Authenticate to Firestore with the JSON account key.
key_dict = json.loads(st.secrets['textkey'])
creds = service_account.Credentials.from_service_account_info(key_dict)
db = firestore.Client(credentials=creds)

# Define the API key
api_key = st.secrets["gmap_api_key"]

gmaps = googlemaps.Client(key=api_key)

# Create a reference to the Google post.
user_collection = db.collection("users")


def get_available_users(collection):
    res = collection.get() # returns a list

    name_list = [doc.to_dict().get("name") for doc in res]    
    lat_list = [doc.to_dict().get("location").latitude for doc in res]
    lng_list = [doc.to_dict().get("location").longitude for doc in res]
            
    
    return name_list, lat_list, lng_list


def get_geocode_from_location(location):
    geocode = gmaps.geocode(location)

    # Print the latitude and longitude of the address
    location = geocode[0]["geometry"]["location"]
    
    latitude = location.get("lat")
    longitude = location.get("lng")

    return latitude, longitude


def delete_collection(coll_ref, batch_size=4):
    docs = coll_ref.list_documents(page_size=batch_size)
    deleted = 0

    for doc in docs:
        doc.delete()
        deleted = deleted + 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)


def delete_particular_user(coll_ref, user_number):
    docs = coll_ref.list_documents()

    for i, doc in enumerate(docs):
        if user_number == i:
            doc.delete()


st.title("Meet in the Middle")

with st.form("input_form", clear_on_submit=True):
   name = st.text_input(label="Name", key="name_key")
   location = st.text_input(label="Location", key="location_key")
   keywords = st.text_input(label="Keywords to search (Restaurants, Colleges etc)", value="badminton")

   # Every form must have a submit button.
   submitted = st.form_submit_button("Submit")
   if submitted:
        if name == "":
            st.error("Enter a valid name")
            st.stop()
        if location == "":
            st.error("Enter your location")
            st.stop()
        if keywords == "":
            st.error("Please enter what you want to search for")
            st.stop()

        lat, lng = get_geocode_from_location(location)
        geolocation = firestore.GeoPoint(latitude=lat, longitude=lng)

        user_collection.document().set({
            "name": name,
            "location_string": location,
            "location": geolocation,
        })


userlist, lat_list, lng_list = get_available_users(collection=user_collection)
# st.write(userlist)
# st.write(lat_list)
# st.write(lng_list)



if userlist:
    with st.expander(label="Click to see the list of users"):
        st.write(userlist)

    usernum_inp, but_col1, but_col2 = st.columns([1, 1, 1])
    user_id = usernum_inp.number_input(label="User Number", min_value=0, max_value=len(userlist)-1)
    but_col1.button(label="Delete", on_click=delete_particular_user, args=[user_collection, user_id])
    delete_all_users_button = but_col2.button(label='Delete all Users', on_click=delete_collection, args=[user_collection,])

    midpoint_lat = np.mean(lat_list)
    midpoint_lng = np.mean(lng_list)

    nearest_courts = gmaps.places_nearby(
        location=(midpoint_lat, midpoint_lng), 
        keyword=keywords, 
        rank_by="distance",
    )

    # st.write(nearest_courts)
    target_location = nearest_courts.get("results")[0].get("geometry").get("location")

    target_lat = target_location.get("lat")
    target_lng = target_location.get("lng")

    # create map object
    m = folium.Map(location=[midpoint_lat, midpoint_lng], zoom_start=12)

    for lat, lng, username in zip(lat_list, lng_list, userlist):
        # add marker for coordinates
        folium.Marker([lat, lng], popup=username).add_to(m)

    # folium.Marker([midpoint_lat, midpoint_lng]).add_to(m)
    folium.Marker([target_lat, target_lng], popup=keywords, icon=folium.Icon(color="green"),).add_to(m)

    st_data = folium_static(m, width=725, )

    st.header("Top 3 places")
    for i in range(3):
        top_result = nearest_courts.get("results")[i]
        place_name = top_result.get("name")
        place_id = top_result.get("place_id")
        place_link = f"https://www.google.com/maps/search/?api=1&query=address&query_place_id={place_id}"


        # st.markdown(body=<)
        st.subheader(f"[{place_name}]({place_link})")
        # st.write(place_link)
        st.markdown("""---""")
