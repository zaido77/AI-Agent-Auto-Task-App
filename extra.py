
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
