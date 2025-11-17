import streamlit as st
import pandas as pd
from pathlib import Path
import os

from extractor import extract_text_from_pdf
from llm_openai import parse_with_openai
from llm_ama import parse_with_ollama

import json
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="LLM PDF Extractor", layout="wide")
OUTPUT_DIR = Path("sample_output")
OUTPUT_DIR.mkdir(exist_ok=True)

st.title(" ZARAPLAST - LLM PDF Extraction")

#provider = st.radio("Choose LLM provider:", ["OpenAI", "Ollama"])

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file:
    pdf_path = OUTPUT_DIR / uploaded_file.name
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.read())

    st.success("PDF uploaded!")

    # ---- Extract text ----
    with st.spinner("Processing Product details..."):
        text, methods = extract_text_from_pdf(str(pdf_path))


    #st.subheader("🔍 Extraction Method")
    #st.write(methods)
    

    #st.subheader("📜 Extracted Text")
    #st.text_area("Result", value=text[:4000], height=300)
    
    data = json.loads(text)
    product_rows = []
    for product in data["products"]:
        flat = product.copy()
        attrs = flat.pop("attributes")  # remove attributes dict
        # Expand attributes into main dict
        for key, value in attrs.items():
            flat[f"attr_{key}"] = value
        product_rows.append(flat)

    st.markdown("#### Product details")
    df = pd.DataFrame(product_rows)

    # If more than one product, show products side-by-side (pivot)
    if len(df) > 1:
        
        # Transpose with product index as column names
        df_vertical = df.set_index(df.index.astype(str)).T
        df_vertical = df_vertical.reset_index().rename(columns={"index": "field"})
        df_vertical = df_vertical[df_vertical["value"].astype(str).str.strip() != ""]

        st.dataframe(df_vertical, use_container_width=True)

    # If only one product, show field/value layout
    else:
        
        df_vertical = df.T
        df_vertical.columns = ["value"]   # safe because only 1 column
        df_vertical = df_vertical.reset_index().rename(columns={"index": "field"})
        df_vertical = df_vertical[df_vertical["value"].astype(str).str.strip() != ""]

        st.dataframe(df_vertical, use_container_width=True)

    st.markdown("#### Customer details")

    df_meta = pd.DataFrame([data["metadata"]])

    # If metadata contains more than one row (very rare), pivot wide
    if len(df_meta) > 1:
        df_vertical_metadata = df_meta.set_index(df_meta.index.astype(str)).T
        df_vertical_metadata = df_vertical_metadata.reset_index().rename(columns={"index": "field"})
        df_vertical_metadata = df_vertical_metadata[df_vertical_metadata["value"].astype(str).str.strip() != ""]

        st.dataframe(df_vertical_metadata, use_container_width=True)

    # Otherwise (normal case), show vertical field | value
    else:
        df_vertical_metadata = df_meta.T
        df_vertical_metadata.columns = ["value"]       # safe with 1 column
        df_vertical_metadata = df_vertical_metadata.reset_index().rename(columns={"index": "field"})
        df_vertical_metadata = df_vertical_metadata[df_vertical_metadata["value"].astype(str).str.strip() != ""]

        st.dataframe(df_vertical_metadata, use_container_width=True)    
    
    
    # ---- LLM Parsing ----
    # if st.button("Run LLM Parsing"):
    #     with st.spinner("Parsing with LLM..."):
    #         if provider == "OpenAI":
    #             result = parse_with_openai(text)
    #         else:
    #             result = parse_with_ollama(text)

    #     st.success("LLM parsing complete!")

    #     st.subheader("📦 Parsed JSON")
    #     st.json(result.dict())

    #     # ---- Convert items to CSV ----
    #     if result.items:
    #         df = pd.DataFrame([i.dict() for i in result.items])
    #         st.subheader("🧾 Parsed Items (CSV Table)")
    #         st.dataframe(df)

    #         csv_path = OUTPUT_DIR / (pdf_path.stem + "_parsed.csv")
    #         df.to_csv(csv_path, index=False)

    #         st.download_button(
    #             label="Download CSV",
    #             data=df.to_csv(index=False).encode("utf-8"),
    #             file_name=pdf_path.stem + "_parsed.csv",
    #             mime="text/csv"
    #         )
