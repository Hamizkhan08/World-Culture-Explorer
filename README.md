<p align="center">
  <img src="static/favicon.png" alt="World Cultural Explorer" width="80"/>
</p>

<h1 align="center">🌍 World Cultural Explorer</h1>

<p align="center">
  <b>An immersive web application to explore the culture, history, cuisine, and heritage of 195 countries — powered by an interactive 3D globe.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Flask-3.x-black?logo=flask" alt="Flask"/>
  <img src="https://img.shields.io/badge/SQLite-Database-07405E?logo=sqlite" alt="SQLite"/>
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License"/>
</p>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🌐 **Interactive 2D/3D Map** | Switch between a Leaflet 2D map and a WebGL-powered 3D globe to explore countries |
| 📊 **Country Details** | View population, capital, currency, flag, and curated fun facts for each country |
| 🎬 **Video Documentaries** | Auto-fetched YouTube travel documentaries embedded on every country page |
| 🧠 **Culture Quiz** | Dynamic quiz engine with country-specific trivia and auto-generated questions |
| ❤️ **Favorites System** | Save and manage your favorite countries (requires login) |
| 📝 **User Reviews** | Post reviews on any country's page |
| 🌙 **Dark/Light Theme** | Toggle between dark and light mode across all pages |
| 📱 **Fully Responsive** | Mobile-optimized UI with a dedicated navigation drawer |
| 🔐 **Authentication** | Register/login system with hashed passwords via Werkzeug |

---

## 🖼️ Pages

- **Landing Page** — Premium hero section with animated feature cards
- **Map View** — Interactive 2D map & 3D globe with country search
- **Country Details** — Stats, fun facts carousel, resource cards (Food/Travel/Culture), embedded video, quiz modal, and reviews
- **Login / Register** — Auth pages with session-based login via Flask-Login

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python, Flask, Flask-Login, Flask-SQLAlchemy |
| **Database** | SQLite (via SQLAlchemy ORM) |
| **Frontend** | HTML5, CSS3, Bootstrap 5, Font Awesome |
| **Maps** | Leaflet.js (2D), Globe.gl (3D WebGL) |
| **APIs** | [REST Countries](https://restcountries.com), Wikipedia API, YouTube Data API v3 |

---

## 📁 Project Structure

```
world/
├── app.py                 # Main Flask application (routes, API, quiz engine)
├── models.py              # SQLAlchemy models (User, Review, Favorite)
├── requirements.txt       # Python dependencies
├── reviews.db             # SQLite database (auto-generated)
├── favicon.ico            # Favicon
├── static/
│   ├── favicon.png        # Favicon PNG
│   ├── food.jpg           # Default food image
│   ├── travel.jpg         # Default travel image
│   └── clothing.jpg       # Default culture image
└── templates/
    ├── landing.html       # Landing/home page
    ├── index.html         # Map explorer (2D & 3D globe)
    ├── details.html       # Country details page
    ├── login.html         # Login page
    └── register.html      # Registration page
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** installed
- **pip** package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Hamizkhan08/World-Culture-Explorer.git
   cd World-Culture-Explorer
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   ```
   http://127.0.0.1:5000
   ```

---

## 🔑 API Keys (Optional)

The app uses the **YouTube Data API v3** to fetch travel documentaries. A default key is included for demo purposes. To use your own:

1. Get a key from [Google Cloud Console](https://console.cloud.google.com/)
2. Replace `YOUTUBE_API_KEY` in `app.py`

> **Note:** The app works fully without YouTube — it gracefully falls back to a search link.

---

## 📡 External APIs Used

| API | Purpose |
|---|---|
| [REST Countries v3.1](https://restcountries.com) | Country stats (population, currency, capital, flag) |
| [Wikipedia API](https://www.mediawiki.org/wiki/API:Main_page) | Hero images for country pages |
| [YouTube Data API v3](https://developers.google.com/youtube/v3) | Travel documentary video embedding |

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License**.

---

<p align="center">
  Made with ❤️ for the culturally curious.
</p>
