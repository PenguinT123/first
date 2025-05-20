import streamlit as st
import pandas as pd

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

# 필수 과목 (삭제 불가)
fixed_subjects = ["국어", "수학", "영어", "한국사"]
# 선택 과목: 대분류만 표시하고 하위과목은 사용자가 추가
category_subjects = ["사회", "과학"]
initial_subjects = fixed_subjects + category_subjects

# 기본 데이터프레임 생성
data = pd.DataFrame(columns=["과목"] + columns)
for subj in initial_subjects:
    row = {"과목": subj}
    for sem in selected_semesters:
        row[sem] = 1.0
    row["반영비율 (%)"] = 100
    data.loc[len(data)] = row

data = data.set_index("과목")

# 데이터 입력 UI
st.header("📊 내신 등급 및 반영비율 입력")
st.caption("※ 하위 과목은 예: 사회 | 사회문화, 과학 | 화학1 형식으로 입력해 주세요.")

edited_data = st.data_editor(
    data,
    num_rows="dynamic",  # 사용자가 하위 과목 추가 가능
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

# 삭제 방지 안내
missing_required = [s for s in fixed_subjects if s not in edited_data.index]
if missing_required:
    st.error(f"❗ 필수 과목({', '.join(missing_required)})은 삭제할 수 없습니다. 다시 추가해주세요.")

# 하위 과목 시각화 (선택)
# st.subheader("📌 과목 목록 미리보기 (구조 확인용)")
# for subject in edited_data.index:
#    if " | " in subject:
#        category, sub = subject.split(" | ")
#        st.markdown(f"- **{category}**의 하위 과목 → `{sub}`")


# 평균 계산 함수
def calculate_weighted_average(df, selected_semesters):
    total_score = 0
    total_weight = 0

    for subject, row in df.iterrows():
        try:
            weight = float(row["반영비율 (%)"])
            if weight == 0:
                continue
        except:
            continue

        semester_scores = [float(row[sem]) for sem in selected_semesters if sem in row and pd.notna(row[sem])]
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
    elif 3.2 <= avg < 3.6:
        return "🎓 수도권 대학교"
    elif avg >= 3.6:
        return "🎓 전문대 중심 고려, 수도권 외 일반대"
    else:
        return "⚠️ 유효한 등급 범위가 아닙니다."
    

# 평균 계산 및 결과 출력
st.header("📈 평균 등급 및 추천 대학 라인")

if st.button("📊 평균 등급 계산하기"):
    average = calculate_weighted_average(edited_data, selected_semesters)
    st.subheader("🎯 평균 등급")
    st.success(f"평균 등급: {average}" if average is not None else "입력된 데이터가 부족합니다.")

    st.subheader("🎓 추천 대학 라인")
    st.info(recommend_universities(average))
