import streamlit as st
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from last_entry import process_last_entry

# --- AWS CONFIG ---
BUCKET_NAME = "apllos-zarplast-poc"
UPLOAD_PREFIX = "user-files-upload/"  # Folder in S3
region_name = "us-east-1"

s3_client = boto3.client("s3", region_name = "us-east-1")

# --- Streamlit UI ---
st.title("ZARAPLAST")
#st.write("All files will be stored in:")
#st.code(f"s3://{BUCKET_NAME}/{UPLOAD_PREFIX}")

uploaded_file = st.file_uploader("Choose a file", type=None)

if uploaded_file is not None:
    file_name = uploaded_file.name
    s3_key = f"{UPLOAD_PREFIX}{file_name}"

    # Clicking upload button
    if st.button("Upload to S3"):
        try:
            s3_client.upload_fileobj(uploaded_file, BUCKET_NAME, s3_key)

            st.success(f"File successfully uploaded to S3!")
            st.code(f"s3://{BUCKET_NAME}/{s3_key}")

            # ---------------------------
            # RUN CLAUDE PROCESSING
            # ---------------------------
            st.write("🤖 Processing with Claude…")
            result = process_last_entry(file_name)

            #st.text_area("Claude Output", result, height=350)
            st.subheader("Claude Output")
            st.markdown(result)


        except NoCredentialsError:
            st.error("❌ AWS Credentials not found.")
        except ClientError as e:
            st.error(f"❌ AWS Error: {e}")
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")


