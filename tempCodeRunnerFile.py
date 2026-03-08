from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import requests
import wikipediaapi
from models import db, Review, User, Favorite # Ensure User and Favorite are imported
import os
import re
import random

app = Flask(__name__)

# --- CONFIGURATION ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'reviews.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# SECURITY KEY: Change this to a random string in production
app.config['SECRET_KEY'] = 'world_explorer_secret_key_12345'

# OPTIONAL: YouTube Key
YOUTUBE_API_KEY = 'AIzaSyCEGdF-PPhVzhRkzZHsSoM5HvtXgVrhjIA' 

# --- INIT EXTENSIONS ---
db.init_app(app)

# Setup Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to 'login' route if user isn't logged in

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

wiki_wiki = wikipediaapi.Wikipedia(
    user_agent='WorldExplorerPro/34.0 (contact@example.com)',
    language='en'
)

with app.app_context():
    db.create_all()

# ==========================================
# FAVORITE FEATURE
# ==========================================
@app.route('/toggle_favorite/<country_name>')
@login_required
def toggle_favorite(country_name):
    # Check if already saved
    existing = Favorite.query.filter_by(user_id=current_user.id, country_name=country_name).first()
    
    if existing:
        db.session.delete(existing) # Remove
        flash(f'Removed {country_name} from favorites.', 'info')
    else:
        new_fav = Favorite(user_id=current_user.id, country_name=country_name)
        db.session.add(new_fav) # Add
        flash(f'Added {country_name} to favorites!', 'success')
        
    db.session.commit()
    return redirect(url_for('country_details', country_name=country_name))

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose another.', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(username=username)
        new_user.set_password(password) # Hashes the password
        db.session.add(new_user)
        db.session.commit()
        
        # Log them in immediately
        login_user(new_user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('home'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('landing_page'))

# ==========================================
# MAIN ROUTES
# ==========================================

@app.route('/')
def landing_page():
    """Show the Landing Page instead of the App directly."""
    return render_template('landing.html', current_user=current_user)

@app.route('/map')
def home():
    # Pass 'user' to template to show Login/Logout buttons
    return render_template('index.html', user=current_user)

@app.route('/country/<country_name>')
def country_details(country_name):
    reviews = Review.query.filter_by(country=country_name).order_by(Review.date_posted.desc()).all()
    
    # Check if user saved this country
    is_saved = False
    if current_user.is_authenticated:
        if Favorite.query.filter_by(user_id=current_user.id, country_name=country_name).first():
            is_saved = True

    # Pass 'user' to template to show Review form only if logged in
    return render_template('details.html', country=country_name, reviews=reviews, user=current_user, is_saved=is_saved)

@app.route('/add_review', methods=['POST'])
@login_required # Protect this route
def add_review():
    country = request.form.get('country')
    comment = request.form.get('comment')
    
    # Use current_user.username instead of form input
    new_review = Review(country=country, user_name=current_user.username, comment=comment)
    db.session.add(new_review)
    db.session.commit()
    
    return redirect(url_for('country_details', country_name=country))

# ==========================================
# DATA & QUIZ ENGINES
# ==========================================

# --- HYBRID QUIZ ENGINE ---
custom_trivia = {
    "India": [
        {"q": "Which white marble mausoleum is a world wonder?", "opts": ["Taj Mahal", "Red Fort", "Qutub Minar", "Hawa Mahal"], "a": "Taj Mahal"},
        {"q": "What is the festival of lights called?", "opts": ["Diwali", "Holi", "Eid", "Pongal"], "a": "Diwali"}
    ],
    "Japan": [
        {"q": "What is the highest mountain in Japan?", "opts": ["Mount Fuji", "Mount Kita", "Mount Hotaka", "Mount Yari"], "a": "Mount Fuji"},
        {"q": "Which traditional garment is associated with Japan?", "opts": ["Kimono", "Sari", "Hanbok", "Cheongsam"], "a": "Kimono"}
    ],
    "Italy": [
        {"q": "Which city is known as the 'Eternal City'?", "opts": ["Rome", "Milan", "Venice", "Florence"], "a": "Rome"},
        {"q": "What is the shape of Italy often compared to?", "opts": ["A Boot", "A Leaf", "A Square", "A Star"], "a": "A Boot"}
    ],
}

def generate_smart_quiz(country_name, data):
    questions = []
    
    # Safe data extraction
    capital = data.get('capital', ['N/A'])[0] if data.get('capital') else 'N/A'
    region = data.get('region', 'Unknown')
    currencies = data.get('currencies', {})
    currency = "Unknown"
    if currencies:
        currency = list(currencies.values())[0].get('name', 'Unknown')

    # Pools
    wrong_caps = ["Paris", "Tokyo", "Berlin", "Madrid", "Rome", "Cairo", "Ottawa", "Canberra", "Brasilia", "Beijing"]
    wrong_currs = ["Euro", "Yen", "Dollar", "Pound", "Rupee", "Won", "Real", "Peso", "Franc"]

    # Q1: Capital
    distractors = [x for x in wrong_caps if x != capital]
    opts = random.sample(distractors, 3) + [capital]
    random.shuffle(opts)
    questions.append({"id": 1, "question": f"What is the capital city of {country_name}?", "options": opts, "answer": capital})

    # Q2: Currency
    distractors = [x for x in wrong_currs if x != currency]
    opts = random.sample(distractors, 3) + [currency]
    random.shuffle(opts)
    questions.append({"id": 2, "question": f"Which currency is used in {country_name}?", "options": opts, "answer": currency})

    # Q3: Region
    wrong_regs = ["Europe", "Asia", "Africa", "Oceania", "Americas", "Antarctic"]
    distractors = [x for x in wrong_regs if x != region]
    opts = random.sample(distractors, 3) + [region]
    random.shuffle(opts)
    questions.append({"id": 3, "question": f"Geographically, {country_name} is located in:", "options": opts, "answer": region})

    # Q4: Borders
    has_borders = "Yes" if data.get('borders') else "No"
    questions.append({"id": 4, "question": f"Does {country_name} share land borders with other countries?", "options": ["Yes", "No"], "answer": has_borders})

    # Custom Trivia Injection
    if country_name in custom_trivia:
        ct = custom_trivia[country_name]
        for i, q in enumerate(ct):
            questions.append({"id": 5 + i, "question": q['q'], "options": q['opts'], "answer": q['a']})

    return questions

# --- MULTI-SOURCE FUN FACTS SYSTEM ---
def get_fun_facts(country_name):
    facts = []
    
    # 1. Hand-Curated Cultural Database
    cultural_facts_db = {
        "India": [
            "🎬 India produces more movies annually than any other country, with Bollywood leading the way.",
            "🍛 There are over 2,000 distinct ethnic groups in India, each with unique cuisines.",
            "🪔 The game of Chess originated in India around the 6th century.",
            "🎨 India has 38 UNESCO World Heritage Sites including the Taj Mahal."
        ],
        "Japan": [
            "🍣 Japan has the highest number of Michelin-starred restaurants in the world.",
            "🌸 Cherry blossom viewing (Hanami) is a centuries-old tradition celebrated nationwide.",
            "🎎 Japan has over 6,800 islands, but only 430 are inhabited.",
            "🏯 There are over 25,000 temples and shrines across Japan."
        ],
        "Italy": [
            "🍕 Pizza Margherita was created in Naples in 1889, named after Queen Margherita.",
            "🎭 Italy has more UNESCO World Heritage Sites (58) than any other country.",
            "🎵 Italy is the birthplace of opera, which began in Florence in the late 16th century.",
            "☕ Italians rarely drink cappuccino after 11 AM - it's considered a breakfast drink!"
        ],
        "France": [
            "🥐 France produces over 400 different types of cheese.",
            "🗼 The Eiffel Tower was originally intended to be temporary, built for the 1889 World's Fair.",
            "🎨 The Louvre is the world's most visited museum with over 10 million visitors annually.",
            "🍷 French law requires radio stations to play at least 40% French music."
        ],
        "Brazil": [
            "⚽ Brazil is the only country to have played in every FIFA World Cup.",
            "🎉 Rio's Carnival is the world's largest carnival, attracting 2 million people per day.",
            "🌳 The Amazon rainforest covers 60% of Brazil's territory.",
            "🎵 Bossa Nova music originated in Brazil in the 1950s."
        ],
        "Egypt": [
            "🏛️ The Great Pyramid of Giza was the tallest structure for over 3,800 years.",
            "📜 Ancient Egyptians invented paper (papyrus), ink, and the 365-day calendar.",
            "😺 Ancient Egyptians worshipped cats and it was illegal to harm them.",
            "💍 Cleopatra was actually Greek, not Egyptian - she was part of the Ptolemaic dynasty."
        ],
        "China": [
            "🧧 Red is considered a lucky color and is used extensively in celebrations.",
            "🥢 Chopsticks have been used in China for over 3,000 years.",
            "🎆 China invented fireworks, paper, printing, and the compass.",
            "🐼 Giant pandas have been on Earth for 2-3 million years."
        ],
        "United States": [
            "🗽 The Statue of Liberty was a gift from France in 1886.",
            "🎬 Hollywood produces about 700 movies per year.",
            "🍔 The hamburger was invented in the USA, despite its German name.",
            "🏈 The Super Bowl is the second-largest food consumption day after Thanksgiving."
        ],
        "Mexico": [
            "🌶️ Mexico has the most diverse cuisine, with 7 regions recognized by UNESCO.",
            "💀 Day of the Dead (Día de los Muertos) is a joyful celebration honoring ancestors.",
            "🎨 Mexico gave the world chocolate, corn, and chili peppers.",
            "🏛️ Mexico City is built on top of the ancient Aztec city of Tenochtitlan."
        ],
        "Australia": [
            "🦘 Kangaroos outnumber people in Australia - there are 50 million kangaroos vs 26 million people.",
            "🏖️ Australia has over 10,000 beaches - you could visit a new beach every day for 27 years!",
            "🎭 The Sydney Opera House has over 1 million roof tiles from Sweden.",
            "🕷️ Australia is home to 21 of the world's 25 most venomous snakes."
        ],
        "Germany": [
            "🍺 Germany has over 1,300 breweries producing more than 5,000 varieties of beer.",
            "🏰 Germany has more than 25,000 castles - the most in the world.",
            "🎄 The Christmas tree tradition originated in Germany in the 16th century.",
            "🚗 The Autobahn has sections with no speed limits."
        ],
        "Spain": [
            "💃 Flamenco music and dance originated in Andalusia, southern Spain.",
            "🎉 Spain has more than 3,000 festivals (fiestas) every year.",
            "🥘 Paella, Spain's famous dish, originated in Valencia.",
            "🕐 Spain has the longest lunch break in Europe, with siestas still common."
        ],
        "Canada": [
            "🍁 Canada has more lakes than the rest of the world combined.",
            "🏒 Ice hockey is Canada's official winter sport, and lacrosse is the summer sport.",
            "🥞 Canadians consume more macaroni and cheese than any other nation.",
            "🗣️ Canada has two official languages: English and French."
        ],
        "Russia": [
            "🎭 The Hermitage Museum in St. Petersburg employs cats to guard against rodents.",
            "🚂 The Trans-Siberian Railway is the longest railway line in the world at 9,289 km.",
            "🎨 Russian nesting dolls (Matryoshka) were inspired by Japanese wooden dolls.",
            "❄️ Russia spans 11 time zones, more than any other country."
        ],
        "South Korea": [
            "🎮 South Korea is the world's most connected country with 95% internet penetration.",
            "🎤 K-pop generates over $10 billion annually for South Korea's economy.",
            "🍜 Korean kimchi has over 200 varieties and is a UNESCO cultural heritage.",
            "📱 Samsung and LG, both Korean companies, are global tech leaders."
        ],
        "Thailand": [
            "🐘 Elephants are Thailand's national animal and symbol of royal power.",
            "🌶️ Thai cuisine balances five flavors: sweet, sour, salty, bitter, and spicy.",
            "🙏 There are over 40,000 Buddhist temples in Thailand.",
            "🏝️ Thailand has over 1,430 islands, including famous ones like Phuket and Koh Samui."
        ],
        "United Kingdom": [
            "☕ The British drink 165 million cups of tea every day.",
            "👑 The Queen (or King) technically owns all the swans in England.",
            "🎭 Shakespeare invented over 1,700 words still used in English today.",
            "🚇 The London Underground is the world's oldest metro system, opened in 1863."
        ],
        "Argentina": [
            "⚽ Argentina has won the FIFA World Cup 3 times (1978, 1986, 2022).",
            "🥩 Argentine beef is world-famous and asado (barbecue) is a national tradition.",
            "💃 Tango music and dance originated in Buenos Aires in the 1880s.",
            "🍷 Argentina is the 5th largest wine producer in the world."
        ],
        "Turkey": [
            "☕ Turkey gave the world coffee - Turkish coffee is UNESCO-recognized.",
            "🕌 Istanbul is the only city in the world located on two continents.",
            "🧿 The evil eye (Nazar) charm is a traditional Turkish symbol of protection.",
            "🎈 Hot air ballooning in Cappadocia is one of the world's most scenic experiences."
        ],
        "Greece": [
            "🏛️ Ancient Greece gave us democracy, the Olympics, and philosophy.",
            "🫒 Greece produces more olive oil per capita than any other country.",
            "🏝️ Greece has over 6,000 islands, but only 227 are inhabited.",
            "🎭 Greek theater masks had built-in megaphones to amplify actors' voices."
        ],
        "Netherlands": [
            "🌷 The Netherlands exports 4.2 billion tulip bulbs annually.",
            "🚲 There are more bicycles than people in the Netherlands.",
            "🧀 The Dutch consume an average of 17.4 kg of cheese per person per year.",
            "🌊 About 26% of the Netherlands is below sea level."
        ],
        "South Africa": [
            "🗣️ South Africa has 11 official languages, the most of any country.",
            "🦏 South Africa is home to 80% of the world's rhino population.",
            "🏔️ Table Mountain in Cape Town is one of the oldest mountains on Earth.",
            "🎵 South Africa is the birthplace of the vuvuzela horn."
        ],
        "New Zealand": [
            "🥝 There are more sheep in New Zealand than people (6:1 ratio).",
            "🎬 The Lord of the Rings trilogy was filmed entirely in New Zealand.",
            "🏉 Rugby is practically a religion in New Zealand - the All Blacks are legendary.",
            "🐧 New Zealand was the last major landmass to be inhabited by humans."
        ],
        "Sweden": [
            "🎵 ABBA, Spotify, and Roxette all come from Sweden.",
            "🍬 Swedish candy (godis) consumption is among the highest in the world.",
            "⚖️ Sweden has been at peace for over 200 years - since 1814.",
            "🏠 IKEA was founded in Sweden and its products are named after Swedish words."
        ],
        "Norway": [
            "🌌 Norway is one of the best places in the world to see the Northern Lights.",
            "🏔️ Norway has more electric cars per capita than any other country.",
            "🐟 Salmon farming is one of Norway's biggest industries.",
            "⛷️ Cross-country skiing was invented in Norway."
        ],
        "Switzerland": [
            "🍫 Switzerland consumes more chocolate per capita than any other country (11 kg/year).",
            "⏰ Swiss watches make up 50% of the world's luxury watch market.",
            "🏔️ Switzerland has 208 mountains over 3,000 meters high.",
            "🧀 There are over 450 varieties of Swiss cheese."
        ],
        "Portugal": [
            "🥚 Portugal invented the egg tart (pastel de nata) in the 18th century.",
            "🌊 Portugal has the longest bridge in Europe - the Vasco da Gama Bridge.",
            "⚽ Cristiano Ronaldo, one of soccer's greatest players, is Portuguese.",
            "🎵 Fado music is a UNESCO Intangible Cultural Heritage from Portugal."
        ],
        "Ireland": [
            "☘️ St. Patrick's Day is celebrated in more countries than any other national festival.",
            "🍺 Guinness brewery in Dublin was leased for 9,000 years at £45 per year.",
            "🎭 Ireland has won the Eurovision Song Contest 7 times, more than any country.",
            "📚 Ireland has produced 4 Nobel Prize winners in Literature."
        ],
        "Poland": [
            "🎹 Chopin, one of the greatest composers, was Polish.",
            "🥟 Pierogi (dumplings) are Poland's national dish with countless varieties.",
            "🏰 Poland has 17 UNESCO World Heritage Sites.",
            "🦬 The European bison (żubr) is Poland's national animal."
        ],
        "Vietnam": [
            "☕ Vietnam is the world's 2nd largest coffee exporter after Brazil.",
            "🏍️ There are over 45 million motorcycles in Vietnam.",
            "🍜 Pho (Vietnamese soup) has been enjoyed for over 100 years.",
            "🏞️ Ha Long Bay has over 1,600 limestone islands and islets."
        ],
        "Indonesia": [
            "🏝️ Indonesia consists of over 17,000 islands across 3 time zones.",
            "🌋 Indonesia has the most active volcanoes of any country - 130 active ones.",
            "🐉 Komodo dragons are found only in Indonesia.",
            "🗣️ Over 700 languages are spoken across Indonesia."
        ],
        "Malaysia": [
            "🌺 Malaysia is one of 17 megadiverse countries with extreme biodiversity.",
            "🏢 The Petronas Towers were the tallest buildings in the world from 1998-2004.",
            "🍛 Malaysian cuisine blends Malay, Chinese, Indian, and Thai influences.",
            "🦧 Orangutans are native to Malaysia and found in Borneo."
        ],
        "Singapore": [
            "🌆 Singapore is both a city and a country - a city-state.",
            "✈️ Changi Airport has been voted world's best airport multiple times.",
            "🚫 Chewing gum is banned in Singapore (with few exceptions).",
            "🌳 Despite being urban, 47% of Singapore is covered with greenery."
        ],
        "Philippines": [
            "📱 Filipinos send the most text messages in the world.",
            "🏝️ The Philippines has over 7,640 islands.",
            "🎤 Karaoke was invented in the Philippines, not Japan.",
            "🎄 The Philippines has the longest Christmas season, starting in September."
        ],
        "Chile": [
            "🌶️ Chile is named after the Chili pepper, despite not being the largest producer.",
            "🌌 Chile's Atacama Desert is the driest place on Earth.",
            "🍇 Chile is the 5th largest wine exporter in the world.",
            "🗿 Easter Island (Rapa Nui) with its famous Moai statues belongs to Chile."
        ],
        "Peru": [
            "🏔️ Machu Picchu, one of the New Seven Wonders, is in Peru.",
            "🦙 Peru has the largest population of alpacas and llamas in the world.",
            "🌽 Peru has over 4,000 varieties of potatoes.",
            "🎵 The pan flute (zampoña) is a traditional Peruvian instrument."
        ],
        "Colombia": [
            "☕ Colombian coffee is considered some of the best in the world.",
            "💐 Colombia is the world's leading exporter of flowers, especially roses.",
            "🎨 Botero, famous for his 'fat' sculptures, is Colombian.",
            "🦋 Colombia has the most bird species of any country - over 1,900."
        ],
        "Morocco": [
            "🍵 Moroccan mint tea is a symbol of hospitality and served in ornate pots.",
            "🏜️ The Sahara Desert covers much of Morocco's eastern regions.",
            "🕌 Morocco has some of the most beautiful mosques in the Islamic world.",
            "🎨 Moroccan zellige tilework is a centuries-old art form."
        ],
        "Kenya": [
            "🦁 Kenya is home to the Great Wildebeest Migration, one of nature's greatest spectacles.",
            "🏃 Kenya produces some of the world's best marathon runners.",
            "☕ Kenyan coffee is renowned for its bright acidity and full body.",
            "🌍 The Great Rift Valley runs through Kenya, creating stunning landscapes."
        ],
        "Nigeria": [
            "🎬 Nollywood (Nigeria's film industry) is the 2nd largest in the world by volume.",
            "🗣️ Over 500 languages are spoken in Nigeria.",
            "🥁 Afrobeat music was pioneered by Nigerian legend Fela Kuti.",
            "⚽ Nigeria has won the Africa Cup of Nations 3 times."
        ],
    }
    
    # Try to get facts from the curated database first
    if country_name in cultural_facts_db:
        facts = cultural_facts_db[country_name].copy()
        return facts[:4]
    
    # If not in database, try alternate country names
    alt_names = {
        "United States of America": "United States",
        "USA": "United States",
        "UK": "United Kingdom",
        "England": "United Kingdom",
        "South Korea": "South Korea",
        "Republic of Korea": "South Korea",
    }
    
    if country_name in alt_names:
        alt_country = alt_names[country_name]
        if alt_country in cultural_facts_db:
            facts = cultural_facts_db[alt_country].copy()
            return facts[:4]
    
    # 2. Dynamic Fallback (REST API)
    try:
        r = requests.get(f"https://restcountries.com/v3.1/name/{country_name}?fullText=true", timeout=3)
        if r.status_code == 200:
            country_data = r.json()[0]
            
            languages = country_data.get('languages', {})
            if languages:
                lang_list = list(languages.values())
                if len(lang_list) == 1:
                    facts.append(f"🗣️ The official language is {lang_list[0]}.")
                elif len(lang_list) > 1:
                    facts.append(f"🗣️ {country_name} has {len(lang_list)} official languages including {lang_list[0]}.")
            
            population = country_data.get('population', 0)
            if population > 1000000:
                facts.append(f"👥 It has a population of over {population:,} people.")
            
            drive_side = country_data.get('car', {}).get('side', '')
            if drive_side:
                facts.append(f"🚗 People drive on the {drive_side} side of the road.")
            
            currencies = country_data.get('currencies', {})
            if currencies:
                curr_name = list(currencies.values())[0].get('name', '')
                if curr_name:
                    facts.append(f"💰 The currency is the {curr_name}.")
            
    except Exception as e:
        print(f"REST Countries error: {e}")
    
    # Ensure we always have 4 facts
    generic_facts = [
        f"🌍 {country_name} has a rich cultural heritage worth exploring.",
        f"🎭 Traditional arts and crafts are an important part of {country_name}'s identity.",
        f"🍽️ The local cuisine of {country_name} reflects centuries of culinary tradition.",
        f"🎉 {country_name} celebrates numerous festivals throughout the year."
    ]
    
    while len(facts) < 4:
        facts.append(generic_facts[len(facts)])
    
    return facts[:4]

def get_hero_image(search_term):
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrsearch": search_term, "gsrlimit": 3, "prop": "imageinfo", "iiprop": "url"}
        headers = { "User-Agent": "WorldExplorerPro/33.0" }
        r = requests.get(url, params=params, headers=headers, timeout=3)
        data = r.json()
        pages = data.get('query', {}).get('pages', {})
        for k, v in pages.items():
            if 'imageinfo' in v:
                img_url = v['imageinfo'][0]['url']
                if img_url.lower().endswith(('.jpg', '.jpeg', '.png')): return img_url
        return "" 
    except: return ""

# --- UPDATED: STRICT YOUTUBE FILTER ---
def get_video_id(country_name):
    if not YOUTUBE_API_KEY or 'YOUR_YOUTUBE' in YOUTUBE_API_KEY: return None
    try:
        # 1. Search Query: Force "Explore" context
        search_query = f"Explore {country_name} travel documentary"
        
        # 2. API Call: Fetch 10 results, Strict SafeSearch
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=10&q={search_query}&type=video&videoEmbeddable=true&safeSearch=strict&key={YOUTUBE_API_KEY}"
        
        r = requests.get(url)
        data = r.json()
        
        if 'items' in data and len(data['items']) > 0:
            target_start = f"explore {country_name}".lower()
            
            # STRATEGY 1: Strict - Title MUST start with "Explore {Country}"
            for item in data['items']:
                title = item['snippet']['title'].lower()
                # Clean punctuation (e.g. "Explore: India" -> "explore india")
                clean_title = re.sub(r'[^\w\s]', '', title)
                
                if clean_title.startswith(target_start) or title.startswith(target_start):
                    return item['id']['videoId']
            
            # STRATEGY 2: Fallback - Title CONTAINS "Explore {Country}"
            for item in data['items']:
                title = item['snippet']['title'].lower()
                if target_start in title:
                    return item['id']['videoId']
            
            # STRATEGY 3: Ultimate Fallback - Use first result (safest bet from strict search)
            return data['items'][0]['id']['videoId']
            
    except Exception as e:
        print(f"YouTube Error: {e}")
        return None
    return None

@app.route('/api/country_data/<country_name>')
def get_country_data(country_name):
    data = {
        "stats": { "population": "N/A", "currency": "N/A", "capital": "N/A", "flag": "/static/travel.jpg" },
        "fun_facts": [], 
        "video_id": None,
        "images": { "hero": "", "food": "/static/food.jpg", "travel": "/static/travel.jpg", "culture": "/static/clothing.jpg" },
        "quiz": [] 
    }

    try:
        r = requests.get(f"https://restcountries.com/v3.1/name/{country_name}?fullText=true")
        
        if r.status_code == 200:
            c = r.json()[0]
            data['stats']['population'] = "{:,}".format(c.get('population', 0))
            
            cap_list = c.get('capital', ['N/A'])
            cap = cap_list[0] if isinstance(cap_list, list) and len(cap_list) > 0 else 'N/A'
            data['stats']['capital'] = cap
            data['stats']['flag'] = c.get('flags', {}).get('svg', '')
            
            currencies = c.get('currencies', {})
            curr = "N/A"
            if currencies:
                first_curr = list(currencies.keys())[0]
                curr = currencies[first_curr].get('name', 'N/A')
            data['stats']['currency'] = curr

            data['quiz'] = generate_smart_quiz(country_name, c)
            
    except Exception as e:
        print(f"Stats Error: {e}")

    data['fun_facts'] = get_fun_facts(country_name)
    data['images']['hero'] = get_hero_image(f"{country_name} landscape nature")
    data['video_id'] = get_video_id(country_name)

    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)