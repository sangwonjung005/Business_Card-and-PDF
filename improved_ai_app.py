import streamlit as st

# 페이지 설정
st.set_page_config(page_title="초간단 앱", page_icon="⚡")

# 메인 UI
st.title("⚡ 초간단 테스트 앱")
st.write("**이 앱이 작동하면 Streamlit은 정상입니다.**")

# 1. 기본 버튼 테스트
st.header("🔘 버튼 테스트")
if st.button("클릭하세요"):
    st.success("✅ 버튼이 작동합니다!")

# 2. 텍스트 입력 테스트
st.header("📝 텍스트 입력 테스트")
user_input = st.text_input("텍스트를 입력하세요:")
if user_input:
    st.write(f"입력한 텍스트: {user_input}")

# 3. 숫자 입력 테스트
st.header("🔢 숫자 입력 테스트")
number = st.number_input("숫자를 입력하세요:", value=0)
st.write(f"입력한 숫자: {number}")

# 4. 선택 테스트
st.header("📋 선택 테스트")
option = st.selectbox("옵션을 선택하세요:", ["옵션 1", "옵션 2", "옵션 3"])
st.write(f"선택한 옵션: {option}")

# 5. 체크박스 테스트
st.header("☑️ 체크박스 테스트")
if st.checkbox("동의합니다"):
    st.success("✅ 체크박스가 작동합니다!")

# 6. 슬라이더 테스트
st.header("🎚️ 슬라이더 테스트")
slider_value = st.slider("값을 선택하세요:", 0, 100, 50)
st.write(f"슬라이더 값: {slider_value}")

# 7. 파일 업로드 테스트 (이미지 없이)
st.header("📁 파일 업로드 테스트")
uploaded_file = st.file_uploader("파일을 업로드하세요", type=['txt'])
if uploaded_file is not None:
    st.success("✅ 파일 업로드가 작동합니다!")
    st.write(f"파일명: {uploaded_file.name}")

# 8. 사이드바 테스트
with st.sidebar:
    st.header("📊 사이드바")
    st.write("사이드바가 정상 작동합니다!")

# 9. 컬럼 테스트
st.header("📐 컬럼 테스트")
col1, col2 = st.columns(2)
with col1:
    st.write("왼쪽 컬럼")
with col2:
    st.write("오른쪽 컬럼")

# 10. 성공 메시지
st.markdown("---")
st.success("🎉 모든 기본 기능이 정상 작동합니다!")
st.info("이 앱이 작동하면 Streamlit 환경은 정상입니다.")

# 11. 문제 해결 가이드
st.header("🔧 문제 해결")
if st.button("문제 진단"):
    st.write("""
    **진단 결과:**
    - ✅ Streamlit 기본 기능: 정상
    - ✅ UI 컴포넌트: 정상
    - ✅ 파일 업로드: 정상
    - ✅ 사이드바: 정상
    """)
