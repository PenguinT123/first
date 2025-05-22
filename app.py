import streamlit as st
import pandas as pd
import altair as alt
import tempfile
import pdfkit

st.set_page_config(page_title="내신 기반 대학 추천", layout="wide")

st.markdown("<h1 style='text-align: center; font-size: 100px;'>🐧</h1>", unsafe_allow_html=True)
st.title("🎓 내신 기반 대학 추천 앱")
st.write("이 앱은 내신 등급을 입력받아 평균을 계산하고 대학 라인을 추천해줍니다.")


# 학기 선택
st.header("📆 입력할 학기 선택")
semester_map = {
    "1-1": "1학년 1학기",
    "1-2": "1학년 2학기",
    "2-1": "2학년 1학기",
    "2-2": "2학년 2학기",
    "3-1": "3학년 1학기",
}
selected_semesters = []
cols = st.columns(len(semester_map))
for i, (code, label) in enumerate(semester_map.items()):
    if cols[i].toggle(label, key=code, value=(i < 2)):
        selected_semesters.append(code)

columns = selected_semesters + ["이수단위", "카테고리"]

fixed_subjects = ["국어", "수학", "영어", "한국사"]
category_subjects = ["사회", "과학"]
initial_subjects = fixed_subjects + category_subjects

# 이모지 포함 카테고리 옵션
category_options = {
    "🟥 국어": "국어",
    "🟧 수학": "수학",
    "🟨 영어": "영어",
    "🟩 사회": "사회",
    "🟦 과학": "과학",
    "🟪 한국사": "한국사",
    "⬜ 그 외": "그 외"
}

# 데이터 초기화 또는 병합
if "grade_data" not in st.session_state:
    df = pd.DataFrame(columns=["과목"] + columns)
    for subj in initial_subjects:
        row = {"과목": subj}
        for sem in selected_semesters:
            row[sem] = None
        row["이수단위"] = 1
        row["카테고리"] = next(k for k, v in category_options.items() if v == subj) if subj in category_options.values() else "⬜ 그 외"
        df.loc[len(df)] = row
    df = df.set_index("과목")
    st.session_state.grade_data = df
    st.session_state.prev_semesters = selected_semesters
else:
    if st.session_state.prev_semesters != selected_semesters:
        df = st.session_state.get("_latest_edited", st.session_state.grade_data.copy())
        for sem in selected_semesters:
            if sem not in df.columns:
                df[sem] = None
        for sem in st.session_state.prev_semesters:
            if sem not in selected_semesters and sem in df.columns:
                df.drop(columns=sem, inplace=True)
        st.session_state.grade_data = df
        st.session_state.prev_semesters = selected_semesters

data = st.session_state.grade_data

st.header("📊 내신 등급 및 이수단위 입력")
st.caption("※ 카테고리를 지정하세요. &nbsp;&nbsp;&nbsp;&nbsp; ※ '이수단위'=일주일 수업시간 &nbsp;&nbsp;&nbsp;&nbsp; ※ 과목 추가 가능")

edited_data = st.data_editor(
    data,
    num_rows="dynamic",
    use_container_width=True,
    key="grade_editor",
    column_order=columns,
    column_config={
        **{
            col: st.column_config.NumberColumn(
                label=col,
                min_value=1.0,
                max_value=9.0,
                step=0.1,
            ) for col in selected_semesters
        },
        "이수단위": st.column_config.NumberColumn(
            label="이수단위",
            min_value=0.5,
            max_value=10.0,
            step=0.5,
        ),
        "카테고리": st.column_config.SelectboxColumn(
            label="카테고리",
            options=list(category_options.keys())
        )
    }
)

st.session_state["_latest_edited"] = edited_data

# 점수 변환
grade_to_score = {1: 100, 2: 96, 3: 89, 4: 77, 5: 60, 6: 40, 7: 23, 8: 11, 9: 0}
def interpolate_score(grade):
    if pd.isna(grade): return None
    if grade <= 1: return 100
    if grade >= 9: return 0
    lower, upper = int(grade), int(grade) + 1
    return grade_to_score[lower] * (upper - grade) + grade_to_score[upper] * (grade - lower)

def calculate_filtered_average(df, semesters, filter_option):
    filter_map = {
        "국수영사": ["국어", "수학", "영어", "사회"],
        "국수영사한": ["국어", "수학", "영어", "사회", "한국사"],
        "국수영과": ["국어", "수학", "영어", "과학"],
        "국수영사과": ["국어", "수학", "영어", "사회", "과학"],
        "전체": ["국어", "수학", "영어", "사회", "과학", "한국사", "그 외"]
    }

    df["카테고리"] = df["카테고리"].map(category_options).fillna(df["카테고리"])

    total_weighted_score = 0
    total_units = 0

    for _, row in df.iterrows():
        category = row["카테고리"]
        if category not in filter_map[filter_option]:
            continue

        try:
            units = float(row["이수단위"])
            if units == 0:
                continue
        except:
            continue

        grades = [row[sem] for sem in semesters if pd.notna(row.get(sem))]
        if not grades:
            continue

        avg_grade = sum(grades) / len(grades)
        total_weighted_score += avg_grade * units
        total_units += units

    return round(total_weighted_score / total_units, 2) if total_units else None

def calculate_converted_score(df, semesters, filter_option="전체"):
    filter_map = {
        "국수영사": ["국어", "수학", "영어", "사회"],
        "국수영사한": ["국어", "수학", "영어", "사회", "한국사"],
        "국수영과": ["국어", "수학", "영어", "과학"],
        "국수영사과": ["국어", "수학", "영어", "사회", "과학"],
        "전체": ["국어", "수학", "영어", "사회", "과학", "한국사", "그 외"]
    }

    df["카테고리"] = df["카테고리"].map(category_options).fillna(df["카테고리"])
    total_weighted_score = 0
    total_units = 0

    for _, row in df.iterrows():
        if row["카테고리"] not in filter_map[filter_option]:
            continue

        try:
            units = float(row["이수단위"])
            if units == 0: continue
        except:
            continue

        grades = [row[sem] for sem in semesters if pd.notna(row.get(sem))]
        if not grades: continue

        avg_grade = sum(grades) / len(grades)
        score = interpolate_score(avg_grade)

        total_weighted_score += score * units
        total_units += units

    return round(total_weighted_score / total_units, 2) if total_units else None

def recommend_universities(score):
    """환산 교과 점수를 기준으로 대학 라인 추천"""
    if score is None:
        return "⚠️ 환산 점수가 계산되지 않았습니다."
    if score >= 99.:
        return "🎓 의치한, 서울대 (인서울 최상위)"
    elif score >= 98:
        return "🎓 서울대, 고려대, 연세대 (인서울 최상위)"
    elif score >= 97:
        return "🎓 서강대, 성균관대, 한양대 (인서울 상위)"
    elif score >= 96:
        return "🎓 이화여대, 중앙대, 경희대, 한국외대, 시립대 (인서울 중상위)"
    elif score >= 95:
        return "🎓 건국대, 동국대, 홍익대, 숙명여대 등 (인서울 중위권)"
    elif score >= 93:
        return "🎓 국민대, 세종대, 숭실대, 인하대 등 (인서울 중하위권)"
    elif score >= 91:
        return "🎓 서울과기대, 광운대, 명지대, 가천대 등"
    elif score >= 89:
        return "🎓 명지대, 상명대, 덕성여대, 동덕여대 등"
    elif score >= 86:
        return "🎓 한성대, 삼육대, 서경대 등"
    elif score >= 79:
        return "🎓 수도권 대학교, 지방거점 국립대"
    else:
        return "🎓 전문대 중심 고려, 수도권 외 일반대"

# 평균 계산 버튼 섹션
st.header("📈 평균 등급 및 추천 대학 라인")
st.write("계산할 평균 산출 방식을 선택하세요:")

st.markdown(
    """
    <style>
    div.stButton > button {
        background-color: #f8c47f;
        color: black;
        border-radius: 12px;
        padding: 12px 24px;
        font-size: 20px;
        font-family: "Segoe UI", sans-serif;
        font-weight: bold;
        box-shadow: 2px 2px 5px gray;
        transition: 0.3s;
        border: none;
        margin: 8px;
    }
    div.stButton > button:hover {
        background-color: #f7b95d;
    }
    </style>
    """,
    unsafe_allow_html=True
)

filter_options = ["국수영사", "국수영사한", "국수영과", "국수영사과", "전체"]
button_cols = st.columns(len(filter_options))
for i, label in enumerate(filter_options):
    if button_cols[i].button(label):
        st.session_state.grade_data = edited_data.copy()
        include_etc = label == "전체"
        avg = calculate_filtered_average(edited_data, selected_semesters, label)
        conv = calculate_converted_score(edited_data, selected_semesters, label)
        st.session_state.average = avg
        st.session_state.converted = conv
        st.session_state.recommendation = recommend_universities(conv)

# 출력 결과
if "average" in st.session_state and "converted" in st.session_state:
    st.subheader("🎯 평균 등급 및 환산 교과 점수")
    st.success(f"평균 등급: {st.session_state.average} / 환산 교과 점수: {st.session_state.converted}점")

if "recommendation" in st.session_state:
    st.subheader("🎓 추천 대학 라인")
    st.info(st.session_state.recommendation)




with st.sidebar:
    st.markdown("## 🐧 정보 안내")

    with st.expander("📐 교과 환산 점수 산출 공식"):
        st.markdown("""
        ### 🧮 산출 방식

        각 과목의 **학기별 등급 평균**                      
        → **환산 점수**로 변환                    
        → **이수단위 가중평균 계산**

        **🧾 공식:**

        $$
        \\text{환산 교과 점수} = 
        \\frac{\\sum \\left( \\text{환산등급점수} \\times \\text{이수단위} \\right)}
        {\\sum \\text{이수단위}}
        $$
        """)

    with st.expander("📊 등급별 반영 점수표"):
        st.markdown("""
        ### 🎯 환산 점수 기준표

        | 평균등급 | 환산 점수 |
        |:--------:|:----------:|
        | 1등급     | 100점      |
        | 2등급     | 96점       |
        | 3등급     | 89점       |
        | 4등급     | 77점       |
        | 5등급     | 60점       |
        | 6등급     | 40점       |
        | 7등급     | 23점       |
        | 8등급     | 11점       |
        | 9등급     | 0점        |

        🐧 **Tip:** 등급이 낮을수록 환산 점수가 크게 떨어져요!
        """)





# 과목별 시각화 코드
# 차트 표시 여부를 위한 세션 상태 변수
if "show_chart" not in st.session_state:
    st.session_state.show_chart = False

# 버튼 클릭 → 토글 방식
if st.button("📊 과목별 평균 시각화 보기/숨기기"):
    st.session_state.show_chart = not st.session_state.show_chart

# 버튼이 눌린 경우에만 차트 표시
if st.session_state.show_chart:
    subject_averages = {}
    for subject, row in edited_data.iterrows():
        grades = [row[sem] for sem in selected_semesters if pd.notna(row[sem])]
        if grades:
            subject_averages[subject] = round(sum(grades) / len(grades), 2)

    if subject_averages:
        avg_df = pd.DataFrame({
            "과목": list(subject_averages.keys()),
            "평균 등급": list(subject_averages.values())
        })

        chart = alt.Chart(avg_df).mark_bar(
            cornerRadiusTopLeft=5,
            cornerRadiusTopRight=5
        ).encode(
            x=alt.X(
                "과목:N",
                sort=avg_df["과목"].tolist(),  # 행 순서 유지
                title="과목",
                axis=alt.Axis(labelAngle=0)   # 축 글자 가로
            ),
            y=alt.Y(
                "평균 등급:Q",
                title="평균 등급",
                axis=alt.Axis(labelAngle=0, titleAngle=0, titlePadding=30)
            ),
            color=alt.Color("과목:N", scale=alt.Scale(scheme="set3")),
            tooltip=["과목", "평균 등급"]
        ).properties(
            width=600,
            height=400,
            title="📊 과목별 평균 등급"
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("계산할 데이터가 없습니다.")



## pdf 내보내기
if st.button("📄 PDF로 내보내기"):

    df = st.session_state.grade_data.copy()
    df_reset = df.reset_index()  # 과목이 인덱스에 있을 경우 대비

    # 산출 방식이 선택되지 않았을 경우 "전체" 기준으로 계산
    if "converted" not in st.session_state or "average" not in st.session_state:
        avg = calculate_filtered_average(df, selected_semesters, "전체")
        conv = calculate_converted_score(df, selected_semesters, include_etc=True)
        reco = recommend_universities(conv)
    else:
        avg = st.session_state.average
        conv = st.session_state.converted
        reco = st.session_state.recommendation

    # 과목별 평균 등급 계산
    subject_averages = {}
    for subject, row in df.iterrows():
        grades = [row[sem] for sem in selected_semesters if pd.notna(row[sem])]
        if grades:
            subject_averages[subject] = round(sum(grades) / len(grades), 2)

    subject_avg_html = ""
    if subject_averages:
        subject_avg_html = "<h2>📊 과목별 평균 등급</h2><table border='1'><tr><th>과목</th><th>평균 등급</th></tr>"
        for subj, avg_score in subject_averages.items():
            subject_avg_html += f"<tr><td>{subj}</td><td>{avg_score}</td></tr>"
        subject_avg_html += "</table>"

    # 전체 HTML 콘텐츠 동적 생성
    table_html = df_reset.to_html(index=False, border=1)

    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: "Malgun Gothic", sans-serif; }}
            h1, h2 {{ text-align: center; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 30px; }}
            th, td {{ border: 1px solid black; padding: 8px; text-align: center; }}
        </style>
    </head>
    <body>
        <h1>내신 성적표</h1>
        {table_html}

        <h2>📈 산출 결과</h2>
        <p><strong>평균 등급:</strong> {avg}</p>
        <p><strong>환산 교과 점수:</strong> {conv}점</p>
        <p><strong>추천 대학 라인:</strong> {reco}</p>

        {subject_avg_html}
    </body>
    </html>
    """

    # PDF로 변환
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        config = pdfkit.configuration(wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe")
        pdfkit.from_string(html_content, tmpfile.name, configuration=config)
        with open(tmpfile.name, "rb") as f:
            st.download_button("📄 PDF 다운로드", f, file_name="내신성적표.pdf")