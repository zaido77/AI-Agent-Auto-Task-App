# AutoTask App

**AutoTask App** is a Streamlit web app that help CUD students to scrape course offerings from the [Student Portal](https://cudportal.cud.ac.ae/student/login.asp) using AI Agents and filter them, making it easier to explore and filter understand available courses.

## 🚀 Features

- Login securely with your CUD credentials  
- Scrape and view current course offerings  
- Download results as a CSV file  
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
```

⚠️ **Note:** Due to browser automation limitations, the scraping feature and custom automation via Gemini will not work on Streamlit Cloud. To use these features, please run the app locally.

```bash
streamlit run main.py
```
