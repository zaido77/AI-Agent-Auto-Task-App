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
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
WEBSITE = os.getenv("WEBSITE")
USER_NAME = os.getenv("USER_NAME")
PASSWORD = os.getenv("PASSWORD")

genai.configure(api_key=API_KEY)

# if system is windows
if os.name == 'nt':
	asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

st.set_page_config(page_title="Automation App", page_icon="CUD.png")
#=====Data & Methods=====

class clsCourse(BaseModel):
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

class clsCourseOfferings(BaseModel):
    Courses: List[clsCourse]

controller = Controller(output_model=clsCourseOfferings)

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
    
    st.write("Dont have account?")
    if st.button("Login as Guest"):
        st.session_state.WelcomeName = "Guest"
        st.session_state.StudentInfo["username"] = USER_NAME
        st.session_state.StudentInfo["password"] = PASSWORD
        st.session_state.StudentInfo["term"] = "SP 2024-25"
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
    st.title("Welcome to the Automation App!")
    st.subheader(f"Hello, {st.session_state.WelcomeName}!")
    st.write("Use the tabs below to run your AI Agent tasks or " +
    "Upload and filter extracted course data or " +
    "Ask AI to filter what you need")

def GetLLM():
    llmChoice = st.selectbox("Select LLM", ("Gemini (Cloud-based)", "LMStudio (Local)"))
    if llmChoice == "Gemini (Cloud-based)":
        return ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=API_KEY) 
    else:
        st.error("LMStudio functionality not implemented yet.")
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
    Parsed:clsCourseOfferings = clsCourseOfferings.model_validate_json(FinalResult)
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
        Step 1: Login to {WEBSITE}
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
    

#=====Main=====

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

if not st.session_state.Authenticated:
    LoginPage()

# Automation App Page
else:
    Welcome()

    tab1, tab2, tab3 = st.tabs(["AI Agent Task", "Search & Filter", "AI Query"])

    # Automation Tab
    with tab1:
        st.subheader("Settings")
        LLMChoice = GetLLM()
        DivisionChoice = GetDivision()

        st.divider() #___________________________________________________________

        st.subheader("Scraping Automation")
        st.write("Scrape Course Offerrings with One Click ONLY")

        if st.button("Scrape"):
                with st.spinner("Scraping Course Offerings... Please wait"):
                    asyncio.run(ScrapeOfferings())
                    st.success("Course offerings scraped successfully! CSV saved to Downloads")


        st.divider() #___________________________________________________________

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
        st.subheader("Search & Filter Course Offerings")

        UploadedFile = st.file_uploader("Upload your Course Offerings CSV file", type=["csv"])

        if UploadedFile: 
            LoadedDf = LoadFile(UploadedFile)
            DataFrame = st.session_state.DataFrame = LoadedDf

            if DataFrame is not None: 
                st.success("CSV file loaded successfully!")

                st.divider() 
                st.subheader("Filter Courses")
                
                col1, col2 = st.columns(2) 

                with col1:
                    InstructorSearch = st.text_input("Search by Instructor Name (contains):")

                with col2:
                    YearOptions = ["All", "1st Year (1xx)", "2nd Year (2xx)", "3rd Year (3xx)", "4th Year (4xx)"]
                    YearFilter = st.selectbox("Filter by Year:", options=YearOptions)

                FilteredDf = DataFrame.copy()

                if InstructorSearch:
                    FilteredDf = FilteredDf[FilteredDf['Instructor'].str.contains(InstructorSearch, case=False, na=False)]

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
                st.divider() 
                st.subheader("Filtered Results")

                if FilteredDf.empty: 
                    st.warning("No courses match your current filter criteria")
                else:
                    st.write(f"Found {len(FilteredDf)} matching course sections:")
                    st.dataframe(FilteredDf)

    # Ai Query Tab
    with tab3 :
        st.subheader("Ask AI for filtering")
        UploadedFile = st.file_uploader("Upload your Course Offerings CSV file", type=["csv"], key="tab3")

        if UploadedFile: 
            LoadedDf = LoadFile(UploadedFile)
            DataFrame = st.session_state.DataFrame = LoadedDf
            if DataFrame is not None:
                st.success("CSV file loaded successfully!")

                if st.checkbox("Show Table"):
                    st.dataframe(DataFrame)
    
                st.divider()
    
                st.markdown("**Example Questions:**")
                st.markdown("- Show all courses by Dr. Adel")
                st.markdown("- What courses are available between 10 AM and 3 PM")
                st.markdown("- Show all courses in 2nd year")
    
                #AI-powered question input
                if prompt := st.chat_input("Ask about courses (e.g., 'Show Dr. Said's courses')"):
                    with st.chat_message("user"):
                        st.write(prompt)
    
                    with st.chat_message("assistant"):
                        with st.spinner("Analyzing..."):
                            #get AI response
                            response = QueryAI(prompt, DataFrame)
                            st.write(response)
           
    # Ai Query Tab
    with tab3 :
        st.subheader("Ask AI for filtering")
        UploadedFile = st.file_uploader("Upload your Course Offerings CSV file", type=["csv"], key="tab3")

        if UploadedFile: 
            LoadedDf = LoadFile(UploadedFile)
            DataFrame = st.session_state.DataFrame = LoadedDf
            if DataFrame is not None:
                st.success("CSV file loaded successfully!")

                if st.checkbox("Show Table"):
                    st.dataframe(DataFrame)
    
                st.divider()
    
                st.markdown("**Example Questions:**")
                st.markdown("- Show all courses by Dr. Adel")
                st.markdown("- What courses are available between 10 AM and 3 PM")
                st.markdown("- Show all courses in 2nd year")
    
                #AI-powered question input
                if prompt := st.chat_input("Ask about courses (e.g., 'Show Dr. Said's courses')"):
                    with st.chat_message("user"):
                        st.write(prompt)
    
                    with st.chat_message("assistant"):
                        with st.spinner("Analyzing..."):
                            #get AI response
                            response = QueryAI(prompt, DataFrame)
                            st.write(response)
           
    
    st.divider()
    if st.button("Logout"):
        Logout()