import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="내신 기반 대학 추천", layout="wide")

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

# 과목 컬럼 정의
columns = selected_semesters + ["반영비율 (%)"]

fixed_subjects = ["국어", "수학", "영어", "한국사"]
category_subjects = ["사회", "과학"]
initial_subjects = fixed_subjects + category_subjects

# 학기 변경 시 이전 데이터 저장 및 반영
if "grade_data" not in st.session_state:
    df = pd.DataFrame(columns=["과목"] + columns)
    for subj in initial_subjects:
        row = {"과목": subj}
        for sem in selected_semesters:
            row[sem] = None
        row["반영비율 (%)"] = 100
        df.loc[len(df)] = row
    df = df.set_index("과목")
    st.session_state.grade_data = df
    st.session_state.prev_semesters = selected_semesters
else:
    if "prev_semesters" in st.session_state and st.session_state.prev_semesters != selected_semesters:
        # 학기 토글 변경 감지 시, 현재 입력값을 저장한 뒤 병합
        current_data = st.session_state.get("_latest_edited", st.session_state.grade_data.copy())
        df = current_data.copy()

        for sem in selected_semesters:
            if sem not in df.columns:
                df[sem] = None
        for sem in st.session_state.prev_semesters:
            if sem not in selected_semesters and sem in df.columns:
                df.drop(columns=sem, inplace=True)

        st.session_state.grade_data = df
        st.session_state.prev_semesters = selected_semesters

# 최신 데이터 기반 편집
data = st.session_state.grade_data

st.header("📊 내신 등급 및 반영비율 입력")
st.caption("※ 하위 과목은 예: 사회 | 사회문화, 과학 | 화학1 형식으로 입력해 주세요.")

edited_data = st.data_editor(
    data,
    num_rows="dynamic",
    use_container_width=True,
    key="grade_editor",
    column_order=columns,
    column_config={
        col: st.column_config.NumberColumn(
            label=col,
            min_value=1.0,
            max_value=9.0,
            step=0.1,
        ) if col != "반영비율 (%)" else st.column_config.NumberColumn(
            label="반영비율 (%)",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
        )
        for col in columns
    }
)

# 현재 편집값 임시 저장
st.session_state["_latest_edited"] = edited_data

fixed_subjects = ["국어", "수학", "영어", "한국사"]
missing_required = [s for s in fixed_subjects if s not in edited_data.index]
if missing_required:
    st.error(f"❗ 필수 과목({', '.join(missing_required)})은 삭제할 수 없습니다. 다시 추가해주세요.")

# 평균 계산 함수
def calculate_filtered_average(df, semesters, filter_option):
    def is_selected(subject):
        if filter_option == "국수영사":
            return subject.startswith(("국어", "수학", "영어", "사회"))
        elif filter_option == "국수영사한":
            return subject.startswith(("국어", "수학", "영어", "사회", "한국사"))
        elif filter_option == "국수영과":
            return subject.startswith(("국어", "수학", "영어", "과학"))
        elif filter_option == "국수영사과":
            return subject.startswith(("국어", "수학", "영어", "사회", "과학"))
        elif filter_option == "전체":
            return True
        return False

    total_score = 0
    total_weight = 0

    for subject, row in df.iterrows():
        if not is_selected(subject):
            continue
        try:
            weight = float(row["반영비율 (%)"])
            if weight == 0:
                continue
        except:
            continue

        semester_scores = [float(row[sem]) for sem in semesters if sem in row and pd.notna(row[sem])]
        if not semester_scores:
            continue

        avg_score = sum(semester_scores) / len(semester_scores)
        total_score += avg_score * (weight / 100)
        total_weight += weight / 100

    if total_weight == 0:
        return None
    return round(total_score / total_weight, 2)

# 대학 라인 추천 함수
def recommend_universities(avg):
    if avg is None:
        return "⚠️ 평균 등급이 계산되지 않았습니다."
    if 1.0 <= avg < 1.2:
        return "🎓 의치한, 서울대 (인서울 최상위)"
    elif 1.2 <= avg < 1.4:
        return "🎓 고려대, 연세대 (인서울 최상위)"
    elif 1.4 <= avg < 1.6:
        return "🎓 서강대, 성균관대, 한양대 (인서울 상위)"
    elif 1.6 <= avg < 1.8:
        return "🎓 이화여대, 중앙대, 경희대, 한국외대, 시립대 (인서울 중상위)"
    elif 1.8 <= avg < 2.0:
        return "🎓 건국대, 동국대, 홍익대, 숙명여대 등 (인서울 중위권)"
    elif 2.0 <= avg < 2.3:
        return "🎓 국민대, 세종대, 숭실대, 인하대 등 (인서울 중하위권)"
    elif 2.3 <= avg < 2.6:
        return "🎓 서울과기대, 광운대, 명지대, 가천대 등"
    elif 2.6 <= avg < 2.9:
        return "🎓 명지대, 상명대, 덕성여대, 동덕여대 등"
    elif 2.9 <= avg < 3.2:
        return "🎓 한성대, 삼육대, 서경대 등"
    elif 3.2 <= avg < 3.8:
        return "🎓 수도권 대학교"
    elif avg >= 3.8:
        return "🎓 전문대 중심 고려, 수도권 외 일반대"
    else:
        return "⚠️ 유효한 등급 범위가 아닙니다."

# 평균 계산 섹션
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
        # 평균 계산 시점에만 저장
        st.session_state.grade_data = edited_data.copy()
        average = calculate_filtered_average(st.session_state.grade_data, selected_semesters, label)
        st.subheader("🎯 평균 등급")
        st.success(f"평균 등급: {average}" if average is not None else "입력된 데이터가 부족합니다.")

        st.subheader("🎓 추천 대학 라인")
        st.info(recommend_universities(average))




# 과목별 시각화 코드드
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