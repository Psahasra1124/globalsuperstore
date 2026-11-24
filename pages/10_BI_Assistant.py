import streamlit as st

from utils.assistant import answer_question
from utils.ui import page_header, section_header


df = st.session_state["df"]
page_header(
    "BI Assistant",
    "Ask a supported business question and get an answer calculated from the current filters.",
    "Rule-based analytics",
)
st.info(
    "This assistant uses deterministic calculations only. It does not send data to an external model "
    "or invent results."
)
with st.form("bi_assistant_form"):
    question = st.text_input(
        "Business question",
        placeholder="For example: Which region has the highest sales?",
    )
    submitted = st.form_submit_button("Analyze filtered data", type="primary")

if submitted:
    response, result = answer_question(df, question)
    st.session_state["assistant_response"] = response
    st.session_state["assistant_result"] = result

if "assistant_response" in st.session_state:
    section_header("Answer")
    st.write(st.session_state["assistant_response"])
    result = st.session_state.get("assistant_result")
    if result is not None:
        st.dataframe(result, use_container_width=True, hide_index=True)
