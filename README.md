# 📻 AI Radio Station

**Developed by [@uchihazeno06-pixel](https://github.com/uchihazeno06-pixel)**

An automated, AI-powered news radio station. This web app scrapes the latest global news articles, uses Google Gemini AI to rewrite them into professional broadcast scripts, and generates human-like audio using Microsoft's Neural Text-to-Speech. It then plays them back-to-back like a real radio station.

## ✨ Features
*   **Live Global News:** Pulls from major outlets like Al Jazeera, BBC, CBC, NPR, The Guardian, and Sky News.
*   **AI Scriptwriting:** Uses Google's `gemini-3.8-flash` to translate (if needed) and rewrite articles into conversational 3-paragraph radio scripts.
*   **Realistic AI Voices:** Uses `edge-tts` to generate high-quality, authoritative audio (currently using the `en-US-ChristopherNeural` voice).
*   **Background Processing:** Uses Python background threads so the web server never times out during the AI generation process.
*   **Live Status Updates:** The frontend polls the server to show the user exactly what the AI is doing (e.g., "Scraping: [Article Title]").
*   **Continuous Playback:** Automatically queues and plays stories back-to-back.

## 🛠️ Tech Stack
*   **Backend:** Python, Flask, `feedparser`, `beautifulsoup4`, `edge-tts`, `google-genai`
*   **Frontend:** HTML, CSS, Vanilla JavaScript
*   **Deployment:** Render

## 🚀 How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone https://github.com/uchihazeno06-pixel/AI-Radio-Station.git
   cd AI-Radio-Station
