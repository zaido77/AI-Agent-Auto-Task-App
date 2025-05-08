import streamlit as st
import pandas as pd
import os
import time
from pydantic import BaseModel
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Controller
import asyncio
import csv
import google.generativeai as genai

# if system is windows
if os.name == 'nt':
	asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

st.set_page_config(page_title="AutoTask App", page_icon="utils/CUDLogo.png")
#=====Data & Methods=====

class Course(BaseModel):
    CourseCode: str
    CourseName: str
    Credits: str
    Instructor: str
    Room: str
    Day: str
    StartTime: str
    EndTime: str
    MaxEnrollment: int
    TotalEnrollment: int

class CourseOfferings(BaseModel):
    Courses: List[Course]

controller = Controller(output_model=CourseOfferings)

def LoginPage():
    st.header("CUD Student Portal Login")
    with st.form(key="student_login_form"):
        username = st.text_input("Username", placeholder="202X000XXXX")
        password = st.text_input("Password", type="password")
        term = GetTerm()
        submit_button = st.form_submit_button(label="Login")

        if submit_button:
            if (not username) or (not password) or (not term):
                st.warning("Please fill in all of the fields")
            else:
                st.session_state.WelcomeName = username
                st.session_state.StudentInfo["username"] = username
                st.session_state.StudentInfo["password"] = password
                st.session_state.StudentInfo["term"] = term
                st.session_state.Authenticated = True
                st.success("Login completed successfully")
                time.sleep(2)
                st.rerun()  # Rerun to show the next page
    
    st.write("Not CUD Student?")
    if st.button("Login as Guest"):
        st.session_state.WelcomeName = "Guest"
        st.session_state.Authenticated = True
        st.success("Login completed successfully")
        time.sleep(2)
        st.rerun()  # Rerun to show the next page
    
def Logout():
    st.session_state.Authenticated = False
    if "StudentInfo" in st.session_state:
        del st.session_state.StudentInfo
    st.rerun()

def Welcome():
    st.title("Welcome to the AutoTask App!")
    st.subheader(f"Hello, {st.session_state.WelcomeName}!")
    st.write("This app helps CUD students to easily scrape their course offerings and filter them as they want")
    st.write("Use the tabs below to run your AI Agent tasks or " +
    "Upload and filter extracted course data or " +
    "Ask AI about the courses")

def GetLLM():
    st.markdown("To get your Gemini API key click [here](https://aistudio.google.com/apikey). Copy and Paste it below.")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    if api_key:
        st.session_state.apiKey = api_key
        genai.configure(api_key=st.session_state.apiKey)
        return ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=st.session_state.apiKey)
    else:
        st.warning("Please enter your Gemini API key.")
    return None

def GetDivision():
    Options = ["AID IntDes DNU",
               "BA eBu DNU",
               "BA HrmMgt DNU",
               "BA MktInb DNU",
               "CMS Arabic DNU",
               "Continuing Education",
               "DBA",
               "EAST Tel DNU",
               "General Education",
               "MIT DNU",
               "MKT DNU",
               "Registrar's Office",
               "SAID",
               "SBA",
               "SCMS",
               "SEAST",
               "SEHS",
               "SGS",
               "SGS-RPP",
               ]
    DivisionChoice = st.selectbox("Select Division", Options, index=Options.index("SEAST"))

    return DivisionChoice

def GetTerm():
    termChoice = st.selectbox("Choose Term", ("FA 2025-26", "SU 1 2024-25", "SP 2024-25"), index=2)

    return termChoice

def AIFinalResultToCourseOfferingsList(FinalResult):
    Parsed:CourseOfferings = CourseOfferings.model_validate_json(FinalResult)
    OfferingsList = [Course.model_dump() for Course in Parsed.Courses]
    return OfferingsList

def AppendCourseOfferingsToCSV(OfferingsList, FilePath, FieldNames):
    try:
        with open(FilePath, "a", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FieldNames)
            writer.writerows(OfferingsList)
    except Exception as e:
        st.error(f"An error occurred while adding data to the CSV file: {e}")

async def ScrapeOfferings():
    TermStr = str(st.session_state.StudentInfo.get('term')).replace(' ', '_')
    FileName = f"course_offerings_{TermStr}.csv"
    if os.access("/sdcard/Download", os.W_OK):  # Android
        FilePath = os.path.join("/sdcard/Download", FileName)
    elif os.name == 'nt':  # Windows
        FilePath = os.path.join(os.path.expanduser("~"), "Downloads", FileName)
    else:  # Other systems (Linux, Mac, etc.)
        FilePath = os.path.join("/tmp", FileName)

    #define CSV column headers
    FieldNames = [
    "CourseCode", "CourseName", "Credits", "Instructor", "Room", "Day",
    "StartTime", "EndTime", "MaxEnrollment", "TotalEnrollment"
    ]


    #create a new CSV file with the headers
    with open(FilePath, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FieldNames)
        writer.writeheader()

    Page = 1 #start from the first page

    #keep looping through all course pages
    while True:
        #instructions for the agent
        Task = f"""
        Step 1: Login to "https://cudportal.cud.ac.ae/student/login.asp"
        Step 2: Select the correct Term specified in sensitive_data.
        Step 3: Click on Course Offering Section
        Step 4: Click on Show Filter
        Step 5: Select {DivisionChoice} from Divisions
        Step 6: Apply Filter.
        Step 7: Navigate to page {Page} and wait for it to fully load
        Step 8: Extract only the following info from all courses: Course, Course Name, Credits, Instructor, Room, Days, Start Time, End Time, Max Enrollment, Total Enrollment.

        Only extract data if you are 100% sure the page number is {Page}.  
        If the page number shown is not {Page}, stop and return nothing.
        """
        #extra guidance for the LLM on how to behave
        MessageContext = f"""
        Only extract data if you are 100% sure the page number is {Page}. 
        If the page number shown is not {Page}, stop and return nothing.
        Output Format: Always follow the JSON output format
        Wait Time: Introduce a brief delay (1 second) before performing actions like clicks or navigation to allow pages to load.
        Error Handling: If data for a field is missing (e.g., no instructor listed), represent it appropriately (e.g., empty string or null) but still include the course entry.
        """

        #set up the agent with the scraping task, LLM, data controller, and instructions
        agent = Agent(
        task=Task,
        llm=LLMChoice,
        sensitive_data=st.session_state.StudentInfo,
        controller=controller,
        message_context=MessageContext
        )

        try:
            #run the agent to do the work
            history = await agent.run()
            FinalResult = history.final_result()

            if not FinalResult:
                break

            OfferingsList = AIFinalResultToCourseOfferingsList(FinalResult)

            if not OfferingsList:
                break

            AppendCourseOfferingsToCSV(OfferingsList, FilePath, FieldNames)

            Page += 1  #move to the next page

        except Exception:
            break  

async def RunCustomTaskAutomation():
    agent = Agent(
    task=UserInstruction,
    llm=LLMChoice
    )
    
    history = await agent.run(max_steps=100)
    finalResult = history.final_result()
    if finalResult:
        st.info("AI Agent: " + finalResult)
    else:
        st.error("Something went wrong, check your API Key")

def FilterProcess():
    col1, col2 = st.columns(2) 
    with col1:
        FilterSearch = st.text_input("Filter Search (contains):")
    with col2:
        YearOptions = ["All", "1st Year (1xx)", "2nd Year (2xx)", "3rd Year (3xx)", "4th Year (4xx)"]
        YearFilter = st.selectbox("Filter by Year:", options=YearOptions)
    FilteredDf = DataFrame.copy()
    if FilterSearch:
        mask = FilteredDf.apply(
            lambda row: row.astype(str).str.contains(FilterSearch, case=False, na=False).any(), axis=1
        )
        FilteredDf = FilteredDf[mask]
    if YearFilter != "All":
        if YearFilter == "1st Year (1xx)":
            FilteredDf = FilteredDf[FilteredDf['CourseCode'].str[3] == '1']
        elif YearFilter == "2nd Year (2xx)":
            FilteredDf = FilteredDf[FilteredDf['CourseCode'].str[3] == '2']
        elif YearFilter == "3rd Year (3xx)":
            FilteredDf = FilteredDf[FilteredDf['CourseCode'].str[3] == '3']
        elif YearFilter == "4th Year (4xx)":
            FilteredDf = FilteredDf[FilteredDf['CourseCode'].str[3] == '4']
    # Display Filtered Results
    st.subheader("Filtered Results")
    if FilteredDf.empty: 
        st.warning("No courses match your current filter criteria")
    else:
        st.write(f"Found {len(FilteredDf)} matching course sections:")
        st.dataframe(FilteredDf)

def AIQueryProcess():
    st.markdown("**Example Questions:**")
    st.markdown("- Show all courses by Dr. Adel")
    st.markdown("- What courses are available between 10 AM and 3 PM")
    st.markdown("- Show all courses in 2nd year")
    #AI-powered question input
    if prompt := st.chat_input("Ask about courses (e.g., 'Show Dr. Said's courses')"):
        if not st.session_state.APIKey:
            st.error("Check your API Key")
        else:
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    #get AI response
                    response = QueryAI(prompt, DataFrame)
                    st.write(response)
                
@st.cache_data
def LoadFile(File):
    try:
        DataFrame = pd.read_csv(File)
        return DataFrame
    except Exception as e:
        st.error(f"Error reading CSV file: {e}")
        return None
    
def QueryAI(Prompt, DataFrame):

    #give context to the AI so it knows what data it's analyzing
    context = f"""
    You are an intelligent and helpful assistant for students at Canadian University Dubai (CUD).
    Your job is to answer questions about course data based on the table below.

    The data has these columns: {', '.join(DataFrame.columns)}.

    Sample data (use it to guide your answer):
    {DataFrame.to_string(index=False)}

    Guidelines:
    - Always try to provide the most relevant answer, even if the question is vague or partially incomplete.
    - Use fuzzy or partial matching where needed. 
    - Do not ask for more clarification unless absolutely necessary.
    - Be concise, helpful, and student-friendly.
    - Do not hallucinate data — only use what's in the table.

    Question: {Prompt}
    """
    
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    response = model.generate_content(context)
    return response.text
    
def SetSessionStates():
    if "StudentInfo" not in st.session_state:  
        st.session_state.StudentInfo = {
            "username": None,
            "password": None,
            "term": None,
        }

    if "DataFrame" not in st.session_state:  
        st.session_state.DataFrame = None

    if "Authenticated" not in st.session_state:  
        st.session_state.Authenticated = False

    if "APIKey" not in st.session_state:
        st.session_state.APIKey = None
#=====Main=====

SetSessionStates()

if not st.session_state.Authenticated:
    LoginPage()

# AutoTask App Page
else:
    Welcome()

    tab1, tab2 = st.tabs(["AI Agent Task", "Search & Filter And AI Query"])

    # AI Automation Tab
    with tab1:
        st.subheader("⚙️ Gemini AI Setting")
        LLMChoice = GetLLM()

        st.divider() 

        st.subheader("Scraping Automation")
        DivisionChoice = GetDivision()

        st.write("Scrape Course Offerrings with One Click ONLY")

        if st.button("Scrape"):
            if st.session_state.WelcomeName == "Guest":
                st.error("This feature is allowed for CUD students only")
            else:
                with st.spinner("Scraping Course Offerings... Please wait"):
                    asyncio.run(ScrapeOfferings())
                    st.success("Course offerings scraped successfully! CSV saved to Downloads")


        st.divider() 

        st.subheader("Custom Task Automation")
        st.write("Run you own AI Agent custom task")
            
        UserInstruction = st.text_area("Enter automation instruction",
                                       value="Compare prices between DeepSeek and ChatGPT",
                                       height=68)
        
        if st.button("Run"):
            with st.spinner("Running Custom Task... Please wait"):
                asyncio.run(RunCustomTaskAutomation())
        
    # Search & Filter Tab
    with tab2:        
        st.subheader("Download & Upload")
        st.write("If you're a Guest, you can try Filtering and AI Query by downloading the sample course offerings below:")

        SampleCSVFilePath = "utils/course_offerings_SP_2024-25.csv"
        with open(SampleCSVFilePath, "rb") as f:
            st.download_button(
                label="Download",
                data=f,
                file_name="course_offerings_SP_2024-25.csv",
                mime="text/csv"
            )

        UploadedFile = st.file_uploader("Upload your Course Offerings CSV file", type=["csv"])

        if UploadedFile: 
            LoadedDf = LoadFile(UploadedFile)
            DataFrame = st.session_state.DataFrame = LoadedDf

            if DataFrame is not None: 
                st.success("CSV file loaded successfully!")
                st.divider()

                st.header("🔍 Search & Filter Course Offerings")
                st.subheader("Filter Courses")
                FilterProcess()

            st.divider()                
            st.header("🤖 Ask AI about Courses")
            AIQueryProcess()

    st.divider()
    if st.button("Logout"):
        Logout()