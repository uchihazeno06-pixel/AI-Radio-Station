import os
from dotenv import load_dotenv
import feedparser
from google import genai
import asyncio
import edge_tts
import random
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# --- 1. SETUP ---
# Load the .env file
load_dotenv()

# Read the key from the environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

if not GEMINI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY is missing. Check your .env file.")
    exit()

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

# --- 3. THE SCRAPER (Gets the full story) ---
def get_full_article_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text() for p in paragraphs])
        return text
    except Exception as e:
        return ""

# --- 4. THE RADIO QUEUE ---
@app.route('/get_radio')
def get_radio():
    playlist = []
    used_urls = set()
    
    for i in range(1, 6): # Generate 5 stories
        print(f"\n--- Fetching Story {i} of 5 ---")
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

                response = client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=prompt,
                )
                ai_script = response.text

                audio_filename = f"story_{i}.mp3"
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
                print(f"⚠️ Failed: {e}")
                continue
                
    if not playlist:
        return jsonify({"error": "Failed to generate radio."}), 500
        
    return jsonify(playlist)

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