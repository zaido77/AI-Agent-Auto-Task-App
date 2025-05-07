# Automation App

**Automation App** is a Streamlit web app that scrapes course offerings from the [Canadian University Dubai (CUD)] and answers user questions using Google Gemini AI.

## 🚀 Features

- Login securely with your CUD credentials  
- Scrape and view current course offerings  
- Download results as a CSV file  
- Ask questions about courses using Gemini AI  
- Filter and search through offerings interactively  

## 🛠️ Requirements

- Python 3.11+
- Streamlit
- LangChain
- Playwright
- `google-generativeai`

```bash
pip install -r requirements.txt
playwright install

> ⚠️ **Note:** The scraping feature won't work on Streamlit Community Cloud due to limitations with headless browser automation (Playwright). Run the app locally for full functionality.
