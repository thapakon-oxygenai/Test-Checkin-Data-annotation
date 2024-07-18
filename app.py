import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# ตั้งค่าการเชื่อมต่อกับ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_file("/Users/thapakon/Desktop/Test_python/test_checkin/credentials.json", scopes=scope)
gc = gspread.authorize(credentials)

# ใช้ลิงก์ Google Sheets เพื่อเปิดสเปรดชีต
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1ET_2JOAqsKgHQDbfnA9aSLSVQSBjQHyaiwpd65sSU6o/edit?gid=1949036492#gid=1949036492"
spreadsheet = gc.open_by_url(spreadsheet_url)

# เปิด worksheet ทั้งสอง
annotator_worksheet = spreadsheet.worksheet("Annotator")
checkin_worksheet = spreadsheet.worksheet("Checkin")

# อ่านข้อมูลจาก Google Sheets
annotator_data = annotator_worksheet.get_all_records()
annotator_df = pd.DataFrame(annotator_data)
nicknames = annotator_df["Nickname"].tolist()
name = annotator_df["Name"].tolist()

# ตั้งค่าเริ่มต้นของ session state
if "logged_in_employee" not in st.session_state:
    st.session_state["logged_in_employee"] = None
    st.session_state["is_admin"] = False
    st.session_state["is_office"] = False
    st.session_state["login_page"] = True  # เริ่มต้นที่หน้า "ล็อกอิน"
    st.session_state["dashboard"] = False  # เริ่มต้นที่หน้า "Dashboard" เป็น False

# ฟังก์ชันสำหรับล็อกเอาต์
def logout():
    st.session_state["logged_in_employee"] = None
    st.session_state["is_admin"] = False
    st.session_state["is_office"] = False
    st.session_state["login_page"] = True  # ตั้งค่าสถานะเป็นหน้า "ล็อกอิน"
    st.experimental_rerun()  # รีเฟรชหน้าเว็บ

# ฟังก์ชันสำหรับแสดงหน้า Dashboard
def dashboard():
    st.header("Dashboard")

    # อ่านข้อมูล checkin_df
    checkin_data = checkin_worksheet.get_all_records()
    checkin_df = pd.DataFrame(checkin_data)
    checkin_df['Date'] = pd.to_datetime(checkin_df['Date'])
    
    # เลือกช่วงวันที่ต้องการดูข้อมูล
    date_range = st.date_input("Select date range", [])
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_data = checkin_df[(checkin_df['Date'] >= pd.to_datetime(start_date)) & (checkin_df['Date'] <= pd.to_datetime(end_date))]
        
        # แปลงคอลัมน์ Wages เป็น float
        filtered_data["Wages"] = pd.to_numeric(filtered_data["Wages"], errors='coerce').fillna(0.0)

        st.write("Data in selected range:")
        st.dataframe(filtered_data[['Date', 'Start_time', 'End_time', 'Employee', 'Assessment', 'Wages']], use_container_width=True, hide_index=True)

        total_wages_in_period = filtered_data['Wages'].sum()
        st.write(f"Total Wages in Selected Period: {total_wages_in_period:.2f}")

        # คำนวณค่าเฉลี่ยของ Assessment และแปลงเป็นเกรด
        assessment_scores = {"Excellent": 4, "Good": 3, "Average": 2, "Poor": 1}
        filtered_data["Assessment_Score"] = filtered_data["Assessment"].map(assessment_scores).fillna(0)
        average_assessment = filtered_data.groupby('Employee')['Assessment_Score'].mean().sort_values(ascending=False)
        average_assessment = average_assessment.round().astype(int).replace({4: "Excellent", 3: "Good", 2: "Average", 1: "Poor"})

        # ตั้งค่าจำนวนการ์ดต่อแถว
        cards_per_row = 3
        num_employees = len(average_assessment)

        # แสดงการ์ดของพนักงานแต่ละคนที่มีข้อมูลในช่วงเวลาที่เลือก
        st.subheader("Performance and Wages")
        cols = st.columns(cards_per_row)
        
        for i, (employee, score) in enumerate(average_assessment.items()):
            col = cols[i % cards_per_row]
            bank = annotator_df.loc[annotator_df['Name'] == employee, 'Bank'].values[0]
            bank_account = annotator_df.loc[annotator_df['Name'] == employee, 'Bank_account'].values[0]
            total_wages = filtered_data[filtered_data['Employee'] == employee]['Wages'].sum()
            performance_grade = "Excellent" if score == 4 else "Good" if score == 3 else "Average" if score == 2 else "Poor"
            
            card_html = f"""
            <div style='margin: 10px; padding: 10px; border: 1px solid #ccc; width: 240px; text-align: center;'>
                <p><strong>Employee:</strong> {employee}</p>
                <p><strong>Bank:</strong> {bank}</p>
                <p><strong>Bank Account:</strong> {bank_account}</p>
                <p><strong>Performance Grade:</strong> {performance_grade}</p>
                <p><strong>Total Wages:</strong> {total_wages:.2f}</p>
            </div>
            """
            col.markdown(card_html, unsafe_allow_html=True)

# ตรวจสอบลิงก์ "?logout=true" สำหรับล็อกเอาต์
if st.query_params.get('logout', [None])[0] == 'true':
    logout()

# ส่วนของหน้า "ล็อกอิน"
if st.session_state["login_page"]:
    st.header("Login")
    employee = st.selectbox("Username", name)
    password = st.text_input("Password", type="password")
    login_button = st.button("login")

    if login_button:
        user_data = annotator_df[annotator_df["Name"] == employee]
        if not user_data.empty:
            correct_password = user_data.iloc[0]["Password"]
            if password == correct_password:
                st.session_state["logged_in_employee"] = employee
                st.session_state["is_admin"] = user_data.iloc[0]["Role"] == "Admin"
                st.session_state["is_office"] = user_data.iloc[0]["Role"] == "Office"
                st.session_state["login_page"] = False  # เปลี่ยนสถานะเป็นหน้า "แอปพลิเคชันหลัก"
                st.experimental_rerun()  # รีเฟรชหน้าเว็บ
            else:
                st.error("Incorrect password")
        else:
            st.error("Username not found")

else:
    user_data = annotator_df[annotator_df["Name"] == st.session_state["logged_in_employee"]].iloc[0]
    full_name = user_data["Name"]

    # แบ่งพื้นที่ออกเป็นสองคอลัมน์
    col1, col2 = st.columns([7.5, 1])
    
    with col1:
        st.markdown(f"**{full_name}**")
    
    with col2:
        if st.button("Logout", key="logout_button"):
            logout()  # เรียกใช้งานฟังก์ชันล็อกเอาต์

    if st.session_state["is_admin"]:
        st.header("Admin")

        st.write("Select the week to display")
        today = datetime.today()
        start_of_week = today - timedelta(days=today.weekday())
        week_start = st.date_input("Please select the start date of the week", value=start_of_week)

        week_start_date = pd.to_datetime(week_start)
        week_end_date = week_start_date + timedelta(days=6)

        checkin_data = checkin_worksheet.get_all_records()
        checkin_df = pd.DataFrame(checkin_data)
        checkin_df['Date'] = pd.to_datetime(checkin_df['Date'])

        week_data = checkin_df[(checkin_df['Date'] >= week_start_date) & (checkin_df['Date'] <= week_end_date)]
        week_data = week_data.sort_values(by='Date', ascending=False)

        if "Wages" not in week_data.columns:
            week_data["Wages"] = 0.0
        else:
            week_data["Wages"] = week_data["Wages"].replace('', 0.0)
            week_data["Wages"] = pd.to_numeric(week_data["Wages"], errors='coerce').fillna(0.0)

        week_data["Description"] = week_data.apply(lambda row: f"{row['Date'].strftime('%Y-%m-%d')} | {row['Start_time']} - {row['End_time']} | {row['Employee']}", axis=1)

        st.write("")
        if not week_data.empty:
            selected_description = st.selectbox("Data Annotator:", ["-----"] + week_data["Description"].tolist())

            if selected_description != "-----":
                selected_row = week_data[week_data["Description"] == selected_description]
                if not selected_row.empty:
                    row_index = selected_row.index[0]
                    current_assessment = week_data.loc[row_index, "Assessment"] if "Assessment" in week_data else ""
                    current_wages = week_data.loc[row_index, "Wages"] if "Wages" in week_data and not pd.isna(week_data.loc[row_index, "Wages"]) else 0.0
                    assessment_options = ["-----","Excellent", "Good", "Average", "Poor"]
                    default_assessment = assessment_options.index(current_assessment) if current_assessment in assessment_options else 0
                    assessment = st.selectbox("Assessment", assessment_options, index=default_assessment)
                    wages = st.number_input("Wages", value=float(current_wages), format="%.2f")
                    update_button = st.button("Update")

                    if update_button:
                        checkin_worksheet.update_cell(row_index + 2, 5, assessment)
                        checkin_worksheet.update_cell(row_index + 2, 6, wages)
                        st.success("Data updated successfully")
                        st.experimental_rerun()  # รีเฟรชหน้าเว็บ
        else:
            st.write("No data for this week")

        week_data = checkin_df[(checkin_df['Date'] >= week_start_date) & (checkin_df['Date'] <= week_end_date)]
        week_data = week_data.sort_values(by='Date', ascending=False)
        week_data["Wages"] = week_data["Wages"].replace('', 0.0)
        week_data["Wages"] = pd.to_numeric(week_data["Wages"], errors='coerce').fillna(0.0)
        st.write(f"Weekly data update {week_start_date.strftime('%Y-%m-%d')} to {week_end_date.strftime('%Y-%m-%d')}")
        st.dataframe(week_data[['Date', 'Start_time', 'End_time', 'Employee', 'Assessment', 'Wages']], use_container_width=True, hide_index=True)

        total_wages = week_data["Wages"].sum()
        st.markdown(f"**Total labeled wages:** {total_wages:,.2f}")
        
    if st.session_state["is_office"]:
        st.session_state["dashboard"] = True

    if st.session_state["dashboard"]:
        dashboard()

    if not st.session_state["is_admin"] and not st.session_state["is_office"]:
        st.header("Checkin")

        with st.form("checkin_form"):
            date = datetime.now().strftime("%Y-%m-%d")
            start_time = st.time_input("Start time")
            end_time = st.time_input("End time")
            update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            submitted = st.form_submit_button("Save")

            if submitted:
                checkin_worksheet.append_row([date, str(start_time), str(end_time), st.session_state["logged_in_employee"], "", "", update_time])
                st.success("Data saved successfully")
                st.experimental_rerun()  # รีเฟรชหน้าเว็บ

        checkin_data = checkin_worksheet.get_all_records()
        checkin_df = pd.DataFrame(checkin_data)
        checkin_df['Date'] = pd.to_datetime(checkin_df['Date'])
        checkin_df = checkin_df.sort_values(by='Date', ascending=False)

        if "Assessment" in checkin_df.columns:
            checkin_df = checkin_df.drop(columns=["Assessment"])
        if "Wages" in checkin_df.columns:
            checkin_df = checkin_df.drop(columns=["Wages"])

        st.write("Data Checkin")  
        st.dataframe(checkin_df, use_container_width=True, hide_index=True)