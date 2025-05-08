# AutoTask App

**AutoTask App** is a Streamlit web app that help CUD students to scrape course offerings from the [Student Portal](https://cudportal.cud.ac.ae/student/login.asp) using AI Agents and ask questions about them, making it easier to explore, filter, and understand available courses in a conversational way.

## 🚀 Features

- Login securely with your CUD credentials  
- Scrape and view current course offerings  
- Download results as a CSV file  
- Filter and search through offerings interactively  
- Ask questions about courses using Gemini AI  

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

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).

You are free to use and modify this software for personal and educational purposes, but **commercial use is not allowed**.
