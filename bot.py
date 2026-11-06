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

# Load environment variables from .env file
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

# --- 2. GLOBAL STATUS TRACKER ---
radio_status = {
    "status": "idle", 
    "playlist": []
}

# --- 3. THE VOICE GENERATOR ---
async def generate_audio(text, filename):
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)

# --- 4. THE SCRAPER ---
def get_full_article_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text() for p in paragraphs])
        return text
    except Exception:
        return ""

# --- 5. THE BACKGROUND WORKER ---
def build_radio_playlist():
    global radio_status
    playlist = []
    used_urls = set()
    
    for i in range(1, 6):
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
                raw_text = get_full_article_text(article_url)
                
                if not raw_text or len(raw_text) < 100:
                    raw_text = latest_article.get('summary', latest_article.get('description', ''))

                print(f"🤖 Generating AI Script for: {title}")
                prompt = f"""
                You are a professional radio news anchor. I will give you an article.
                If the article is not in English, translate it to English first.
                Rewrite the article into a detailed 3-paragraph spoken audio script.
                Explain the story clearly and conversationally. Do not include URLs, hashtags, or stage directions.
                
                ARTICLE TEXT:
                {raw_text}
                """

                response = None
                for attempt in range(3):
                    try:
                        response = client.models.generate_content(
                            model='gemini-3.8-flash',
                            contents=prompt,
                        )
                        break
                    except Exception as e:
                        if "503" in str(e):
                            print(f"⚠️ Google busy. Retrying...")
                            time.sleep(3)
                        else:
                            raise e
                            
                if not response: continue

                ai_script = response.text
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
                continue
                
    radio_status["playlist"] = playlist
    radio_status["status"] = "ready"

# --- 6. THE WEB ROUTES ---
@app.route('/start_radio')
def start_radio():
    global radio_status
    radio_status["status"] = "generating"
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
        return jsonify({"status": "generating"})

@app.route('/audio/<filename>')
def serve_audio(filename):
    response = send_from_directory(os.getcwd(), filename)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/')
def serve_index():
    return send_from_directory(os.getcwd(), 'index.html')

if __name__ == "__main__":
    print("🚀 Server starting... Open http://127.0.0.1:5000 in your browser.")
    app.run(port=5000, threaded=True)
