import streamlit as st

st.set_page_config(page_title="About", page_icon="📈")

st.markdown("# About")
st.sidebar.header("About Page")
st.write(
    """This demo illustrates a combination of plotting and animation with
Streamlit. We're generating a bunch of random numbers in a loop for around
5 seconds. Enjoy!"""
)