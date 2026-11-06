# 📻 AI Radio Station

An automated, AI-powered radio station that turns today's global news into a continuous audio broadcast. 

The system scrapes articles from major news outlets, uses Google's Gemini AI to rewrite them into professional 3-paragraph anchor scripts, and generates human-sounding audio using Microsoft Edge-TTS. 

## 🚀 Features
* **Live News Scraping:** Fetches full articles from BBC, Al Jazeera, CBC, NPR, Sky News, and The Guardian via RSS.
* **AI News Anchor:** Uses `gemini-3.8-flash` to translate (if needed) and rewrite articles into conversational broadcast scripts.
* **Realistic Voice Generation:** Converts text to speech using `edge-tts` (Christopher Neural voice).
* **Continuous Playback:** Automatically queues up 5 stories and plays them back-to-back.
* **Live Status UI:** Shows the user exactly what the backend is doing (Scraping, Writing, or Generating Audio) in real-time.

## 🛠️ Tech Stack
* **Backend:** Python, Flask, BeautifulSoup, Feedparser
* **AI & Voice:** Google Gemini API (`google-genai`), `edge-tts`
* **Frontend:** HTML, CSS, JavaScript
* **Deployment:** Render

## 💻 How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/AI-Radio-Station.git
   cd AI-Radio-Station
