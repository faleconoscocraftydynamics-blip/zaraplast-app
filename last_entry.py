import boto3
import json

s3 = boto3.client("s3")
RESULTS_BUCKET = "apllos-zaraplast-bda-results"
region_name = "us-east-1"

import time

def wait_for_bda_results(prefix, timeout=120, interval=5):
    """
    Polls S3 every `interval` seconds until the prefix appears or timeout is reached.
    """
    start = time.time()

    while time.time() - start < timeout:
        response = s3.list_objects_v2(Bucket=RESULTS_BUCKET, Prefix=prefix)

        if "Contents" in response and len(response["Contents"]) > 0:
            return response  # success!

        print(f"⏳ Waiting for BDA results folder {prefix} …")
        time.sleep(interval)

    return None  # timeout


def get_last_s3_object(bucket_name, prefix=None):
    """
    Returns the most recently modified object in the bucket (optionally under a prefix).
    """
    kwargs = {"Bucket": bucket_name}
    if prefix:
        kwargs["Prefix"] = prefix

    response = s3.list_objects_v2(**kwargs)

    if "Contents" not in response:
        return None

    # Sort by LastModified descending (newest first)
    latest = max(response["Contents"], key=lambda x: x["LastModified"])
    
    return {
        "key": latest["Key"],
        "last_modified": latest["LastModified"],
        "size": latest["Size"]
    }

def read_json_from_s3(bucket, key):
    """
    Download and parse JSON file content from S3.
    """
    obj = s3.get_object(Bucket=bucket, Key=key)
    content = obj["Body"].read().decode("utf-8")
    return json.loads(content)

bedrock_client = boto3.client("bedrock-runtime")

def send_to_claude(json_payload):
    """
    Sends JSON content to Claude 3.5 Sonnet using AWS Bedrock.
    """

    prompt = f"""
    Aqui está o JSON. Extrai os detalhes do produto e retorna a resposta em markdown:

    {json.dumps(json_payload, indent=2)}
    """

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = bedrock_client.invoke_model(
        modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
        body=json.dumps(body)
    )

    response_body = json.loads(response["body"].read())
    return response_body["content"][0]["text"]

def main():
    bucket = "apllos-zaraplast-bda-results"

    print("🔍 Getting last S3 object…")
    last_obj = get_last_s3_object(bucket)

    if not last_obj:
        print("❌ No objects found.")
        return

    key = last_obj["key"]
    print(f"📄 Last file: {key}")

    print("📥 Reading JSON…")
    data = read_json_from_s3(bucket, key)

    print("🤖 Sending to Claude Sonnet 4.5…")
    result = send_to_claude(data)

    print("\n===== CLAUDE RESULT =====")
    print(result)
    print("=========================")


def get_last_json_for_uploaded_file(filename_no_ext):
    prefix = f"user-files-upload/{filename_no_ext}/"

    response = s3.list_objects_v2(Bucket=RESULTS_BUCKET, Prefix=prefix)
    contents = response.get("Contents", [])

    # Filter for result.json
    result_files = [obj["Key"] for obj in contents if obj["Key"].endswith("result.json")]

    max_wait_seconds = 120
    retry_interval = 5
    elapsed = 0

    while not result_files and elapsed < max_wait_seconds:
        print(f"⏳ Waiting for result.json inside {RESULTS_BUCKET}/{prefix} …")
        time.sleep(retry_interval)
        elapsed += retry_interval

        response = s3.list_objects_v2(Bucket=RESULTS_BUCKET, Prefix=prefix)
        contents = response.get("Contents", [])
        result_files = [obj["Key"] for obj in contents if obj["Key"].endswith("result.json")]    

    if not result_files:
        return None, f"❌ Timeout: No result.json found in {RESULTS_BUCKET}/{prefix} after {max_wait_seconds}s"

    
    newest_result = max(
        (obj for obj in response["Contents"] if obj["Key"] in result_files),
        key=lambda x: x["LastModified"]
    )

    key = newest_result["Key"]
    data = read_json_from_s3(RESULTS_BUCKET, key)

    return data, key



def process_last_entry(uploaded_filename):
    """
    Runs the logic but returns the response instead of printing (for Streamlit).
    """
    filename_no_ext = uploaded_filename.rsplit(".", 1)[0]
    data, key = get_last_json_for_uploaded_file(filename_no_ext)

    if data is None:
        return key  # error messagei

    result = send_to_claude(data)

    return f"📄 File: {key}\n\n🤖 Claude Response:\n\n{result}"

# Run only when executing python file
if __name__ == "__main__":

    main()
