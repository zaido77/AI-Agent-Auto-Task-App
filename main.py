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
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
WEBSITE = os.getenv("WEBSITE")
USER_NAME = os.getenv("USER_NAME")
PASSWORD = os.getenv("PASSWORD")

if os.name == 'nt':
	asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

#=====Data & Methods=====

# --- NOT USED ---
CourseOfferingsTask = f"""
Step 1: Login to {WEBSITE}
Step 2: Select the correct Term specified in sensitive_data.
Step 3: Click on Course Offering Section
Step 4: Click on Show Filter
Step 5: Select SEAST from Divisions
Step 6: Apply Filter. Wait for Page 1 of results to load.
Step 7: Process pages 1, 2, and 3 sequentially:
        a. For each main course row (Course Code, Course Name, Credits, Max/Total Enr) on the current page:
           - Find all detail rows ("Sections": Instructor, Room, Day, Start/End Time) directly below it.
           - For EACH Section row, create one output dictionary combining the main course data with that Section's data. Store this dictionary (accumulate results).
        b. Navigation:
           - Process page 1 first (already loaded after Step 6).
           - After processing page 1: Find the link with the exact text '2' and click it. Wait for page 2 to load completely. Then process page 2 (repeat step 7a).
           - After processing page 2: Find the link with the exact text '3' and click it. Wait for page 3 to load completely. Then process page 3 (repeat step 7a).
           - Stop processing after completing page 3. Do not click on the link '4' or any higher page numbers.
Step 8: Final Output: Compile ALL stored course dictionaries gathered from only pages 1, 2, and 3 into a single JSON object. Return ONLY this JSON object. 
""" #{ "Courses": [ {course_details_dict_1}, ... ] }

# --- NOT USED ---
MessageContext = """
Data Persistence: Remember and accumulate extracted course data across multiple steps and pages.
Output Format: Always follow the final JSON output format specified in the task: { "Courses": [ list_of_course_dictionaries ] }.
Page Limit: Stop processing after extracting data from the first 3 pages.
Wait Time: Introduce a brief delay (1 second) before performing actions like clicks or navigation to allow pages to load.
Error Handling: If data for a field is missing (e.g., no instructor listed), represent it appropriately (e.g., empty string or null) but still include the course entry.
"""

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
    llmChoice = st.selectbox("Choose LLM", ("Gemini (Cloud-based)", "LMStudio (Local)"))
    if llmChoice == "Gemini (Cloud-based)":
        return ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=API_KEY) 
    else:
        st.error("LMStudio functionality not implemented yet.")
        return None

def GetTerm():
    termChoice = st.selectbox("Choose Term", ("FA 2025-26", "SU 1 2024-25", "SP 2024-25"), index=2)

    return termChoice

def AIFinalResultToCourseOfferingsList(FinalResult):
    Parsed:clsCourseOfferings = clsCourseOfferings.model_validate_json(FinalResult)
    OfferingsList = [Course.model_dump() for Course in Parsed.Courses]
    return OfferingsList

# --- NOT USED ---
def SaveCourseOfferingsToCSV(CourseOfferingsData:clsCourseOfferings):
    TermStr = str(st.session_state.StudentInfo.get('term')).replace(' ', '_')
    FileName = f"course_offerings_{TermStr}.csv"
    DownloadsPath = os.path.join(os.path.expanduser("~"), "Downloads")
    FilePath = os.path.join(DownloadsPath, FileName)

    try:
        CourseOfferingsDictList = [Course.model_dump() for Course in CourseOfferingsData.Courses]
        with open(FilePath, 'w', newline='', encoding='utf-8') as csvFile:
            Writer = csv.DictWriter(csvFile, fieldnames=CourseOfferingsDictList[0].keys()) # if CourseOfferingsDictList else None
            if Writer:
                Writer.writeheader()
                for row in CourseOfferingsDictList:
                    Writer.writerow(row)
                st.success(f"Course offerings scraped successfully!\nCSV saved to: {FilePath}")
    except Exception as e:
        st.error(f"An error occurred while saving the CSV: {e}")
        st.error("Try Again")

def AppendCourseOfferingsToCSV(OfferingsList, FilePath, FieldNames):
    try:
        with open(FilePath, "a", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FieldNames)
            writer.writerows(OfferingsList)
    except Exception as e:
        st.error(f"An error occurred while adding data to the CSV file: {e}")

# --- NOT USED ---
async def RunAgent():
    agent = Agent(
    task=UserInstruction,
    llm=LLMChoice,
    sensitive_data=st.session_state.StudentInfo,
    controller=controller,
    message_context=MessageContext
    )
    
    with st.spinner("Scraping Course Offerings... Please wait"):
        history = await agent.run(max_steps=100)
        finalResult = history.final_result()
        if finalResult:
            CourseOfferingsData:clsCourseOfferings = AIFinalResultToCourseOfferingsList(finalResult)
            if CourseOfferingsData:
                SaveCourseOfferingsToCSV(CourseOfferingsData)
            else:
                st.error("Error: Failed to retrieve course offerings")
        else:
            st.error("An error occured while scraping course offerings")

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
        Step 5: Select SEAST from Divisions
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
    
#=====Main Code=====
st.set_page_config(page_title="3mk Zaid App")

if "StudentInfo" not in st.session_state:
    st.session_state.StudentInfo = {
        "username": None,
        "password": None,
        "term": None
    }

if "Authenticated" not in st.session_state:  
    st.session_state.Authenticated = False

if not st.session_state.Authenticated:
    LoginPage()

# Automation App Page
else:
    Welcome()

    tab1, tab2, tab3 = st.tabs(["LLM Automation", "Upload & Search", "AI Query"])

    # Automation Tab
    with tab1:
        st.write("")
        LLMChoice = GetLLM()

        st.divider()

        st.subheader("Scraping Automation")
        st.write("The scraping feature is helpful for SEAST students only right now")
        st.write("You can scrape Course Offerrings with One Click ONLY")

        if st.button("Scrape"):
                with st.spinner("Scraping Course Offerings... Please wait"):
                    asyncio.run(ScrapeOfferings())
                    st.success("Course offerings scraped successfully! CSV saved to Downloads")


        st.divider()

        st.subheader("Custom Task Automation")
        st.write("You can run you own AI Agent custom task with One Click ONLY")
            
        UserInstruction = st.text_area("Enter automation instruction",
                                       value="Compare prices between DeepSeek and ChatGPT",
                                       height=68)
        
        if st.button("Run"):
            with st.spinner("Running Custom Task... Please wait"):
                asyncio.run(RunCustomTaskAutomation())
        

    # Upload & Search Tab
    with tab2:
        st.subheader("Explore Course Offerings Data")

        UploadedFile = st.file_uploader("Upload your Course Offerings CSV file", type=["csv"])

        if UploadedFile: 
            LoadedDf = LoadFile(UploadedFile) 

            if LoadedDf is not None: 
                st.success("CSV file loaded successfully!")

                st.divider() 
                st.subheader("Filter Courses")
                
                col1, col2 = st.columns(2) 

                with col1:
                    InstructorSearch = st.text_input("Search by Instructor Name (contains):")

                with col2:
                    YearOptions = ["All", "1st Year (1xx)", "2nd Year (2xx)", "3rd Year (3xx)", "4th Year (4xx)"]
                    YearFilter = st.selectbox("Filter by Year:", options=YearOptions)

                FilteredDf = LoadedDf.copy()

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

    with tab3:
        st.error("Not Implemented Yet")
        
    st.divider()
    if st.button("Logout"):
        Logout()
