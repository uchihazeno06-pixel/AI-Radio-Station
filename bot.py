import feedparser
from google import genai
import asyncio
import edge_tts
import random
import os
import requests
import time
import uuid
import threading
from bs4 import BeautifulSoup
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# --- 1. SETUP ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) 

FEEDS = [
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.cbc.ca/webfeed/rss/rss-topstories",
    "http://feeds.bbci.co.uk/news/rss.xml",
    "https://feeds.npr.org/1001/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://feeds.skynews.com/feeds/rss/home.xml"
]

radio_status = {
    "status": "idle", 
    "current_action": "",
    "playlist": []
}

async def generate_audio(text, filename):
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)

def get_full_article_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text() for p in paragraphs])
        return text
    except Exception:
        return ""

def build_radio_playlist():
    global radio_status
    playlist = []
    used_urls = set()
    
    # Only generate 3 stories to guarantee we beat Render's timeout
    for i in range(1, 4): 
        success = False
        random.shuffle(FEEDS)
        
        for chosen_feed in FEEDS:
            if success: break
            try:
                feed = feedparser.parse(chosen_feed, request_headers={'User-Agent': 'Mozilla/5.0'})
                if not feed.entries: continue

                latest_article = feed.entries[0]
                article_url = latest_article.link
                
                if article_url in used_urls: continue
                
                title = latest_article.title
                radio_status["current_action"] = f"Scraping: {title}"
                
                # Fallback 1: Use RSS text if scraping fails
                raw_text = latest_article.get('summary', latest_article.get('description', ''))
                scraped_text = get_full_article_text(article_url)
                
                if scraped_text and len(scraped_text) > 200:
                    raw_text = scraped_text

                radio_status["current_action"] = f"Writing AI script: {title}"
                
                prompt = f"Rewrite this into a 3-paragraph radio script. If not English, translate it. No URLs or hashtags.\n\n{raw_text}"

                response = None
                # Fallback 2: Try two different AI models if the first is busy
                for model_name in ['gemini-3.8-flash', 'gemini-3.8-flash-lite']:
                    try:
                        response = client.models.generate_content(model=model_name, contents=prompt)
                        break
                    except Exception:
                        time.sleep(2)

                # Fallback 3: If AI completely fails, just read the raw text aloud
                if response and response.text:
                    ai_script = response.text
                else:
                    ai_script = raw_text

                radio_status["current_action"] = f"Generating audio: {title}"
                audio_filename = f"story_{uuid.uuid4().hex}.mp3"
                asyncio.run(generate_audio(ai_script, audio_filename))

                playlist.append({
                    "title": title,
                    "source": chosen_feed.split('/')[2].replace('www.', ''),
                    "script": ai_script,
                    "audio_url": f"/audio/{audio_filename}" 
                })
                used_urls.add(article_url)
                success = True
                
            except Exception as e:
                print(f"Error: {e}")
                continue
                
    radio_status["playlist"] = playlist
    radio_status["current_action"] = "Finished!"
    radio_status["status"] = "ready"

@app.route('/start_radio')
def start_radio():
    global radio_status
    radio_status["status"] = "generating"
    radio_status["current_action"] = "Starting up..."
    radio_status["playlist"] = []
    
    thread = threading.Thread(target=build_radio_playlist)
    thread.start()
    
    return jsonify({"message": "Generation started"})

@app.route('/check_status')
def check_status():
    global radio_status
    if radio_status["status"] == "ready":
        return jsonify({"status": "ready", "playlist": radio_status["playlist"]})
    else:
        return jsonify({"status": "generating", "action": radio_status.get("current_action", "Starting up...")})

@app.route('/audio/<filename>')
def serve_audio(filename):
    response = send_from_directory(os.getcwd(), filename)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/')
def serve_index():
    return send_from_directory(os.getcwd(), 'index.html')

if __name__ == "__main__":
    app.run(port=5000, threaded=True)
