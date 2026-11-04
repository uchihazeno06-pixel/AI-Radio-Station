import feedparser
from google import genai
import asyncio
import edge_tts
import random
import os
import requests
import time
import uuid
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

# --- 2. THE VOICE GENERATOR ---
async def generate_audio(text, filename):
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)

# --- 3. THE SCRAPER ---
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

# --- 4. SINGLE STORY GENERATOR ---
@app.route('/get_single_story')
def get_single_story():
    random.shuffle(FEEDS)
    
    for chosen_feed in FEEDS:
        try:
            feed = feedparser.parse(chosen_feed, request_headers={'User-Agent': 'Mozilla/5.0'})
            if not feed.entries: continue

            # Pick a random recent article
            latest_article = random.choice(feed.entries[:5])
            article_url = latest_article.link
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
            for attempt in range(2): # Try twice if Google is busy
                try:
                    response = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=prompt,
                    )
                    break
                except Exception as e:
                    if "503" in str(e):
                        time.sleep(2)
                    else:
                        raise e
                        
            if not response: continue

            ai_script = response.text
            
            # Generate unique file name to avoid browser cache issues
            audio_filename = f"story_{uuid.uuid4().hex}.mp3"
            asyncio.run(generate_audio(ai_script, audio_filename))

            return jsonify({
                "title": title,
                "source": chosen_feed.split('/')[2].replace('www.', ''),
                "script": ai_script,
                "audio_url": f"/audio/{audio_filename}" 
            })
            
        except Exception as e:
            print(f"⚠️ Error with feed: {e}")
            continue

    return jsonify({"error": "Could not fetch any stories."}), 500

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
