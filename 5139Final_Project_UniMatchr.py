# UniMatchr: Find Your Next Higher Ed Match ;)
## By: Stephanie Shin and Lika Davtian

'''
For our final, we have decided to create a website that uses an algorithm to match higher ed institutions to users based off user input.
Users will input desired location of college/university, select preferred tuition range, and choice of acceptance rate. 
Using this input, our code will then generate a list of institutions in the US for the user to filter through.
Like the popular dating app Tindr, based off the profile presented to them, users will "swipe left" (NO) or "swipe right" (YES). 
Once a a few institutions and the user have "matched", then the user can look through the list of matches to learn more about each school.
'''
# importing necessary libraries
import pandas as pd
import numpy as np
import matplotlib as plt
import streamlit as st

# first attempt at creating a website using streamlit 
# st.write("Our first attempt at setting up a website")
# was a success!

st.title("_UniMatchr_: Find Your Next Higher Ed Match ;)")
st.header("Welcome to ***UniMatchr***! Your next perfect match awaits you.")
st.subheader("We are so excited you are allowing us to accompany you on this journey of selecting the right higher education institution for you. :balloon:")
st.subheader("To get started, please click on the button below. We can't wait to show you what we have in store! Your potential matches are so excited to meet you. :heart:")
st.header("Are you ready? :sunglasses:")
st.button("Let's Start!")
