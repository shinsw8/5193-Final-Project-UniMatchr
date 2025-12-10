# UniMatchr: Find Your Next Higher Ed Match ;)
## By: Stephanie Shin and Lika Davtian


# Pages:
# 1) Welcome / Login / Signup
# 2) Preferences (filters)
# 3) Swipe / Match profiles (Tinder-style)
# 4) Liked universities dashboard (list with links)


# importing necessary libraries
import streamlit as st
import requests
import json
import time
from urllib.parse import urlencode


# API keys
SCORECARD_API_KEY = "FAVuIJplGdOCHJ9QSJLvcvra9WlJAdeVuZuM9xPW"
UNSPLASH_ACCESS_KEY = "p-aS1sKZQJhSyIL_Bf9EHWwityUwIwS6LtjXNphMO0o"


# Local storage filename for very small demo user data 
USERS_DB_FILE = "unimatchr_users.json"


# Utilities: simple local user DB
def load_users_db():
   try:
       with open(USERS_DB_FILE, "r", encoding="utf-8") as f:
           return json.load(f)
   except FileNotFoundError:
       return {}


def save_users_db(db):
   with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
       json.dump(db, f, indent=2)


# Utilities: College Scorecard API fetch
def fetch_colleges_from_scorecard(api_key, per_page=100, fields=None, filters=None):
   """
   Fetch up to `per_page` institutions from the College Scorecard API.
   Returns a list of school records (dicts).
   `fields` is a list of field names to request.
   `filters` is a dict of query parameters to pass (e.g., {'school.state': 'CA'})
   """
   base = "https://api.data.gov/ed/collegescorecard/v1/schools"
   params = {
       "api_key": api_key,
       "per_page": per_page,
       "page": 0
   }
   if fields:
       params["fields"] = ",".join(fields)
   if filters:
       # Scorecard filter syntax is a bit special, but we'll pass simple params if provided.
       params.update(filters)
   resp = requests.get(base, params=params, timeout=15)
   resp.raise_for_status()
   data = resp.json()
   return data.get("results", [])


# Utilities: Unsplash image fetch
def fetch_unsplash_for_school(school_name, unsplash_key, width=800, height=500):
   """
   Returns a small dict with image url(s). We use Unsplash Search Photos endpoint.
   Falls back to a placeholder image if nothing found.
   """
   search_url = "https://api.unsplash.com/search/photos"
   params = {
       "query": f"{school_name} campus",
       "client_id": unsplash_key,
       "per_page": 1,
       "orientation": "landscape"
   }
   try:
       r = requests.get(search_url, params=params, timeout=10)
       r.raise_for_status()
       j = r.json()
       if j.get("results"):
           img = j["results"][0]
           # choose regular or small
           return img["urls"].get("regular") or img["urls"].get("small")
   except Exception:
       pass
   # fallback placeholder (data URI or simple placeholder) — we'll use a blank data URL
   return "https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?auto=format&fit=crop&w=1200&q=60"


# Normalize/format school info
def nice_school_card(s):
   """
   Accepts a Scorecard school object and returns a normalized small dict for display.
   Handles missing fields gracefully.
   """
   name = s.get("school.name") or s.get("school", {}).get("name") or s.get("school_name") or "Unknown"
   city = s.get("school.city") or s.get("school", {}).get("city") or ""
   state = s.get("school.state") or s.get("school", {}).get("state") or ""
   url = s.get("school.school_url") or s.get("school", {}).get("school_url") or ""
   id_ = s.get("id") or s.get("school", {}).get("id") or None


   # costs & acceptance
   admission_rate = None
   tuition_in = None
   tuition_out = None
   size = None


   # Scorecard nested keys sometimes use 'latest.' prefix
   admission_rate = s.get("latest.admissions.admission_rate.overall") or s.get("latest", {}).get("admissions", {}).get("admission_rate", {}).get("overall")
   tuition_in = s.get("latest.cost.tuition.in_state") or s.get("latest", {}).get("cost", {}).get("tuition", {}).get("in_state")
   tuition_out = s.get("latest.cost.tuition.out_of_state") or s.get("latest", {}).get("cost", {}).get("tuition", {}).get("out_of_state")
   size = s.get("latest.student.size") or s.get("latest", {}).get("student", {}).get("size")


   # build majors top-10 approximation (Scorecard majors are complex — we'll provide a placeholder if missing)
   majors = s.get("latest.academics.program_percentage")  # may be a dict of CIP codes -> percentages
   top_majors = []
   if isinstance(majors, dict):
       # pull top N by percentage if present
       try:
           top = sorted(majors.items(), key=lambda kv: kv[1] or 0, reverse=True)[:10]
           top_majors = [str(k) for k, v in top if v]
       except Exception:
           top_majors = []
   # If not available, keep empty and UI will note that majors are limited
   return {
       "id": id_,
       "name": name,
       "city": city,
       "state": state,
       "url": f"https://{url}" if url and not url.startswith("http") else url,
       "admission_rate": admission_rate,
       "tuition_in": tuition_in,
       "tuition_out": tuition_out,
       "size": size,
       "top_majors": top_majors,
   }


# ----------------------------
# Streamlit App UI & Pages
# ----------------------------
st.set_page_config(page_title="UniMatchr — Find Your Next Higher Ed Match", layout="centered")


# Initialize session state
if "page" not in st.session_state:
   st.session_state.page = "welcome"  # welcome, preferences, swipe, dashboard
if "user" not in st.session_state:
   st.session_state.user = None
if "users_db" not in st.session_state:
   st.session_state.users_db = load_users_db()
if "filters" not in st.session_state:
   st.session_state.filters = {}
if "schools" not in st.session_state:
   st.session_state.schools = []  # list of normalized school dicts
if "swipe_index" not in st.session_state:
   st.session_state.swipe_index = 0
if "liked" not in st.session_state:
   st.session_state.liked = []  # list of school ids
if "school_images" not in st.session_state:
   st.session_state.school_images = {}  # id -> image url


# Top navigation
st.sidebar.title("UniMatchr")
nav = st.sidebar.radio("Navigate", ["Welcome", "Preferences", "Swipe", "Dashboard"], index=["Welcome","Preferences","Swipe","Dashboard"].index({
   "Welcome":"Welcome","Preferences":"Preferences","Swipe":"Swipe","Dashboard":"Dashboard"}[st.session_state.page.title()]) if False else 0)
# The above radio hack is cumbersome; instead use simple buttons to route:
if st.sidebar.button("Welcome"):
   st.session_state.page = "welcome"
if st.sidebar.button("Preferences"):
   st.session_state.page = "preferences"
if st.sidebar.button("Swipe"):
   st.session_state.page = "swipe"
if st.sidebar.button("Dashboard"):
   st.session_state.page = "dashboard"



# Page 1: Welcome page (signup / login)

def page_welcome():
   st.title("_UniMatchr_: Find Your Next Higher Ed Match ;)")
   st.header("Welcome to ***UniMatchr***! Your next perfect match awaits you.") 
   st.subheader("We are so excited you are allowing us to accompany you on this journey of selecting the right higher education institution for you. :balloon:") 
   st.subheader("To get started, please login button below. We can't wait to show you what we have in store! Your potential matches are so excited to meet you. :heart:") 
   st.header("Are you ready? :sunglasses:")
   st.write("Swipe right to like :heart_eyes:, left to pass :confounded:. Don't forget to login or create an account to save your matches!")
   col1, col2 = st.columns(2)


   with col1:
       st.header("Login")
       login_email = st.text_input("Email", key="login_email")
       login_pwd = st.text_input("Password", type="password", key="login_pwd")
       if st.button("Log in"):
           db = st.session_state.users_db
           user = db.get(login_email)
           if user and user.get("password") == login_pwd:
               st.session_state.user = {"email": login_email, "name": user.get("name")}
               st.success(f"Logged in as {user.get('name') or login_email}")
               # load saved liked list if exists
               st.session_state.liked = user.get("liked", [])
               st.session_state.page = "preferences"
           else:
               st.error("Invalid email or password.")


   with col2:
       st.header("Sign up")
       signup_name = st.text_input("Full name", key="signup_name")
       signup_email = st.text_input("Email (signup)", key="signup_email")
       signup_pwd = st.text_input("Create password", type="password", key="signup_pwd")
       if st.button("Create account"):
           if not signup_email or not signup_pwd:
               st.error("Please provide email and password.")
           else:
               db = st.session_state.users_db
               if signup_email in db:
                   st.error("An account with that email already exists.")
               else:
                   db[signup_email] = {
                       "name": signup_name or signup_email,
                       "password": signup_pwd,
                       "liked": []
                   }
                   save_users_db(db)
                   st.session_state.users_db = db
                   st.success("Account created! Please log in on the left.")
   st.markdown("---")
   st.write("Or continue as a guest (but your matches won't be saved :pensive:).")
   if st.button("Continue as guest"):
       st.session_state.user = {"email": None, "name": "Guest"}
       st.session_state.page = "preferences"


# Page 2: Preferences page (filters)

def page_preferences():
   st.title("Now the fun begins! :lips: ***teehee***")
   st.subheader("Set filters to narrow universities. These filters will be used to fetch and display institutions.")
   st.write("We are sooooooo excited for you! :eye: :tongue: :eye:")


   # Simple filters: location (state), major keyword (text), tuition max, acceptance rate
   states = ["Any","AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"]
   selected_state = st.selectbox("State (location)", states, index=0)
   major_keyword = st.text_input("Major keyword (optional) — this narrows names or campus keywords")
   max_tuition = st.number_input("Max tuition (out-of-state) — leave 0 to ignore", min_value=0, value=0, step=500)
   max_acceptance = st.slider("Max acceptance rate (%) — 100 means include all", 0, 100, 100)
   results_count = st.slider("How many institutions to fetch (approx)", 10, 200, 100)


   if st.button("C'mon! Let's see who fit your needs :raised_hands:"):
       # Build Scorecard filters (we'll use school.state and admission rate)
       filters = {}
       if selected_state and selected_state != "Any":
           filters["school.state"] = selected_state
       # admission rate filter: latest.admissions.admission_rate.overall__range=0..max_acceptance/100
       # Scorecard API expects rates as decimals (0.5 for 50%). We'll use 'latest.admissions.admission_rate.overall__range'
       if max_acceptance < 100:
           filters["latest.admissions.admission_rate.overall__range"] = f"0..{max_acceptance/100:.3f}"


       # fields to request to keep payload small
       fields = [
           "id",
           "school.name",
           "school.city",
           "school.state",
           "school.school_url",
           "latest.admissions.admission_rate.overall",
           "latest.cost.tuition.in_state",
           "latest.cost.tuition.out_of_state",
           "latest.student.size",
           # majors often unavailable; include program_percentage if present
           "latest.academics.program_percentage"
       ]
       with st.spinner("Fetching institutions from College Scorecard..."):
           try:
               raw = fetch_colleges_from_scorecard(SCORECARD_API_KEY, per_page=results_count, fields=fields, filters=filters)
               normalized = [nice_school_card(r) for r in raw]
               # Filter further locally for tuition or major keyword if requested
               if max_tuition > 0:
                   normalized = [s for s in normalized if (s["tuition_out"] is None or s["tuition_out"] <= max_tuition)]
               if major_keyword:
                   # we don't have friendly major names reliably; we'll do a fuzzy match on name/city/state
                   mk = major_keyword.lower()
                   normalized = [s for s in normalized if mk in (s["name"] or "").lower() or mk in (s["city"] or "").lower() or mk in (s["state"] or "").lower()]
               st.session_state.schools = normalized
               st.session_state.filters = {"state": selected_state, "major_keyword": major_keyword, "max_tuition": max_tuition, "max_acceptance": max_acceptance}
               st.session_state.swipe_index = 0
               st.success(f"Fetched {len(normalized)} institutions (locally filtered).")
           except Exception as e:
               st.error(f"Failed to fetch institutions: {e}")
               st.session_state.schools = []



# Page 3: Profiles page (swipe & match)

import streamlit as st


def page_swipe():
   st.title("Okay folks! Let's get rollin' :smirk_cat:")
   if not st.session_state.schools:
       st.info("Oh no! :scream_cat: There are no schools loaded. Go back and set your preferences first.")
       st.write("We're picky! :triumph: We don't want just any old institution :space_invader:")
       st.write("Make sure you're setting your filters to get the schools you ***really*** want :star:")
       if st.button("Go to Preferences :rocket:"):
           st.session_state.page = "preferences"
           st.rerun() # Updated to st.rerun()
       return


   idx = st.session_state.swipe_index
   if idx >= len(st.session_state.schools):
       st.info("You've viewed all fetched institutions.")
       if st.button("Restart swiping from beginning"):
           st.session_state.swipe_index = 0
           st.rerun() # Updated to st.rerun()
       return


   s = st.session_state.schools[idx]
   st.subheader(f"{s['name']} — {s['city']}, {s['state']}")
   # fetch image if not cached
   if s["id"] not in st.session_state.school_images:
       try:
           img = fetch_unsplash_for_school(s["name"], UNSPLASH_ACCESS_KEY)
       except Exception:
           img = None
       st.session_state.school_images[s["id"]] = img
   img_url = st.session_state.school_images.get(s["id"])
   if img_url:
       st.image(img_url, use_column_width=True)


   # Basic info card
   info_md = f"""
**Location:** {s['city']}, {s['state']}
**Tuition (in-state):** {s['tuition_in'] if s['tuition_in'] not in (None, '') else 'N/A'}
**Tuition (out-of-state):** {s['tuition_out'] if s['tuition_out'] not in (None, '') else 'N/A'}
**Acceptance rate:** {f'{s['admission_rate']*100:.1f}%' if s['admission_rate'] not in (None, '') else 'N/A'}
**Average enrollment (students):** {s['size'] if s['size'] else 'N/A'}
"""
   st.markdown(info_md)


   if s["top_majors"]:
       st.markdown("**Top majors (approx):** " + ", ".join(s["top_majors"][:10]))
   else:
       st.markdown("*Top majors data limited for this institution.*")


   # Swipe buttons
   col1, col2, col3 = st.columns([1,1,1])
   with col1:
       if st.button("Nope ⬅️ (Swipe left)"):
           # just advance
           st.session_state.swipe_index += 1
           st.rerun() # Updated to st.rerun()
   with col2:
       if st.button("Open profile (details)"):
           # open a more detailed profile view for current school (inline)
           st.markdown("---")
           st.header(f"{s['name']} — Details")
           st.write("Official website:", s.get("url") or "Not available")
           st.write(info_md)
           st.write("Majors: ", s["top_majors"] or "Not available")
           st.write("You can also click 'Yes' below to save to your liked list.")
   with col3:
       if st.button("Yes ❤️ (Swipe right)"):
           if s["id"] not in st.session_state.liked:
               st.session_state.liked.append(s["id"])
           # persist to user db if logged in
           if st.session_state.user and st.session_state.user.get("email"):
               db = st.session_state.users_db
               userrec = db.get(st.session_state.user["email"], {})
               userrec["liked"] = st.session_state.liked
               db[st.session_state.user["email"]] = userrec
               save_users_db(db)
               st.session_state.users_db = db
           st.session_state.swipe_index += 1
           st.success("Added to your liked list.")
           st.rerun() # Updated to st.rerun()


   # show progress
   st.caption(f"Viewing {idx+1} of {len(st.session_state.schools)}")


# Page 4: List of matches page

def page_dashboard():
   st.title("This is what you've been waiting for.. :revolving_hearts:")
   st.header("Here are your list of matches! They've been waiting for you :kiss: :kissing_smiling_eyes:") 
   st.write("Are you ready for the big reveal?")
   st.title("Your UniMatches :open_book: :books:") 
   st.subheader("Heyyy :wave: Here are the institutions that ***you*** liked, and that liked ***YOU*** :heart_eyes_cat:")
   if not st.session_state.liked:
       st.info("WAIT!!! You haven't liked any institutions yet :scream:")
       st.info("Go back and find your Uni match! They're out there :kissing_heart:")
       if st.button("BRB going to find my matches :cupid:"):
           st.session_state.page = "swipe"
       return


   # Build a lookup id -> school object
   lookup = {s["id"]: s for s in st.session_state.schools}
   # Some liked ids might not be in current fetched set — attempt to fetch minimal info for them
   missing_ids = [sid for sid in st.session_state.liked if sid not in lookup]
   if missing_ids:
       # fetch them by id (single call per id is inefficient but fine for demo)
       fields = ["id","school.name","school.city","school.state","school.school_url","latest.admissions.admission_rate.overall","latest.cost.tuition.in_state","latest.cost.tuition.out_of_state","latest.student.size"]
       for mid in missing_ids:
           try:
               raw = fetch_colleges_from_scorecard(SCORECARD_API_KEY, per_page=1, fields=fields, filters={"id": mid})
               if raw:
                   s = nice_school_card(raw[0])
                   lookup[mid] = s
           except Exception:
               pass


   # Display liked schools
   for sid in st.session_state.liked:
       s = lookup.get(sid)
       if not s:
           st.write(f"School ID {sid} (details unavailable)")
           continue
       cols = st.columns([1,3])
       with cols[0]:
           # show cached image if available; otherwise attempt fetch
           img = st.session_state.school_images.get(sid)
           if not img:
               try:
                   img = fetch_unsplash_for_school(s["name"], UNSPLASH_ACCESS_KEY)
               except Exception:
                   img = None
               st.session_state.school_images[sid] = img
           if img:
               st.image(img, width=150)
       with cols[1]:
           st.subheader(s["name"])
           st.write(f"{s['city']}, {s['state']}")
           st.write(f"Acceptance rate: {f'{s['admission_rate']*100:.1f}%' if s['admission_rate'] else 'N/A'}")
           st.write(f"In-state tuition: {s['tuition_in'] or 'N/A'} | Out-of-state: {s['tuition_out'] or 'N/A'}")
           if s.get("url"):
               st.markdown(f"[Visit official website]({s['url']})")
           if st.button(f"Remove from liked — {s['name']}", key=f"remove_{sid}"):
               st.session_state.liked.remove(sid)
               # persist change if logged in
               if st.session_state.user and st.session_state.user.get("email"):
                   db = st.session_state.users_db
                   userrec = db.get(st.session_state.user["email"], {})
                   userrec["liked"] = st.session_state.liked
                   db[st.session_state.user["email"]] = userrec
                   save_users_db(db)
                   st.session_state.users_db = db
               st.experimental_rerun()


   st.markdown("---")
   if st.button("Export liked list as JSON"):
       to_export = [lookup.get(sid, {"id": sid}) for sid in st.session_state.liked]
       st.download_button("Download JSON", data=json.dumps(to_export, indent=2), file_name="unimatchr_liked.json", mime="application/json")


# ----------------------------
# Router: show the correct page
# ----------------------------
if st.session_state.page == "welcome":
   page_welcome()
elif st.session_state.page == "preferences":
   page_preferences()
elif st.session_state.page == "swipe":
   page_swipe()
elif st.session_state.page == "dashboard":
   page_dashboard()
else:
   # Fallback: default to welcome
   page_welcome()



