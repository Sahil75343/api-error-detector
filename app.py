# ============================================================================
#  SMART API ERROR DETECTION & FIX SUGGESTION  (NO API KEY VERSION)
#  Cognizant Hackathon Project
# ============================================================================
#
#  WHAT THIS APP DOES (in plain English):
#  1. A user pastes a failed API response (a status code + the response body)
#  2. Our "rules layer" instantly labels what KIND of error it is
#  3. Our "knowledge layer" gives a detailed root cause + fix + prevention tip
#  4. We show everything nicely on the screen
#
#  This version needs NO API key, NO internet for the logic, and costs NOTHING.
#  All the intelligence is built directly into this file.
# ============================================================================

import streamlit as st

st.set_page_config(
    page_title="Smart API Error Detector",
    page_icon="🔧",
    layout="centered",
)

# ----------------------------------------------------------------------------
#  THE KNOWLEDGE BASE (our built-in intelligence)
#  For each status code we store the category, severity, meaning, root cause,
#  a concrete fix, and a prevention tip. This replaces an AI call with
#  hand-written expert knowledge — instant, reliable, free, works offline.
# ----------------------------------------------------------------------------
KNOWLEDGE_BASE = {
    400: {
        "category": "Bad Request",
        "severity": "Client Error",
        "meaning": "The request was malformed — something you sent is wrong.",
        "root_cause": "The server couldn't understand the request. Usually the JSON body is invalid, a required field is missing, or a value is the wrong data type.",
        "fix": "Check your request body carefully:\n1. Make sure the JSON is valid (no trailing commas, all quotes closed).\n2. Confirm every REQUIRED field is present.\n3. Check data types match the docs (numbers vs strings vs booleans).\n\nExample: if the API expects {\"age\": 25} don't send {\"age\": \"25\"}",
        "prevention": "Validate your request data on your side BEFORE sending it, and keep the API documentation open while building.",
    },
    401: {
        "category": "Authentication Error",
        "severity": "Client Error",
        "meaning": "You are not authenticated — a missing or invalid API key/token.",
        "root_cause": "The server doesn't know who you are. The API key is missing, misspelled, expired, or not being sent in the right header.",
        "fix": "1. Confirm you're actually sending the key.\n2. Check the header name is EXACTLY what the docs require, e.g.:\n     Authorization: Bearer YOUR_API_KEY\n3. Make sure the key hasn't expired or been revoked.\n4. Watch for accidental spaces or missing the word 'Bearer'.",
        "prevention": "Store keys in environment variables or a secrets manager, and test authentication with a simple call before building further.",
    },
    403: {
        "category": "Permission Denied",
        "severity": "Client Error",
        "meaning": "You ARE authenticated, but you're not allowed to access this.",
        "root_cause": "Your credentials are valid, but your account/role lacks permission for this specific resource or action (a 'scopes' or 'roles' issue).",
        "fix": "1. Check your API key's permissions/scopes in the provider's dashboard.\n2. Confirm your plan or role is allowed to use this endpoint.\n3. If accessing someone's data, confirm you have their authorization.\n4. Some APIs need you to explicitly enable a permission/scope for the key.",
        "prevention": "Request only the scopes you need up front, and document which endpoints require which permission levels.",
    },
    404: {
        "category": "Not Found",
        "severity": "Client Error",
        "meaning": "The endpoint or resource you asked for does not exist.",
        "root_cause": "The URL is wrong, or the specific item (like a user id) doesn't exist. Often a typo in the path or a wrong API version.",
        "fix": "1. Double-check the URL spelling against the docs, character by character.\n2. Confirm the API version in the path is correct (e.g. /v1/ vs /v2/).\n3. If fetching a specific item, confirm that id actually exists.\n4. Check for missing/extra slashes: /users/ vs /users",
        "prevention": "Build endpoint URLs from a single base-URL constant instead of typing them out each time, to avoid typos.",
    },
    408: {
        "category": "Request Timeout",
        "severity": "Client Error",
        "meaning": "The server waited too long for your request and gave up.",
        "root_cause": "Your request took longer than the server's time limit — often a slow connection, a very large payload, or a slow upstream step.",
        "fix": "1. Retry the request — timeouts are often temporary.\n2. Reduce the size of what you're sending if it's large.\n3. Increase your client's timeout setting if the operation is genuinely slow.\n4. Check your own network connection.",
        "prevention": "Add automatic retries with a short delay, and keep payloads lean.",
    },
    422: {
        "category": "Validation Error",
        "severity": "Client Error",
        "meaning": "The request was understood but the data failed validation rules.",
        "root_cause": "The format was fine, but the VALUES broke a business rule — e.g. an invalid email, a password too short, or a date in the past.",
        "fix": "1. Read the response body — 422 responses usually list exactly which fields failed and why.\n2. Fix each listed field to match the rule (format, length, range).\n3. Example: 'email must be valid' → send name@example.com, not name@",
        "prevention": "Mirror the API's validation rules in your own form/input checks so bad data is caught before it's ever sent.",
    },
    429: {
        "category": "Rate Limit Exceeded",
        "severity": "Client Error",
        "meaning": "You sent too many requests too quickly and got throttled.",
        "root_cause": "You crossed the API's allowed number of requests per second/minute/hour. Common when looping over data without any pause.",
        "fix": "1. Slow down — add a short delay between requests.\n2. Check the response headers for 'Retry-After' and wait that long.\n3. Use exponential backoff: wait 1s, then 2s, then 4s between retries.\n4. Batch requests together where the API supports it.",
        "prevention": "Respect the documented rate limits, cache repeated results, and build in backoff so bursts don't hammer the API.",
    },
    500: {
        "category": "Internal Server Error",
        "severity": "Server Error",
        "meaning": "Something broke on the SERVER'S side, not yours.",
        "root_cause": "An unexpected error inside the API itself (a bug or crash on their end). Usually NOT caused by your request being wrong.",
        "fix": "1. Retry after a short wait — it may be a temporary glitch.\n2. Confirm it's not your data by trying a known-good simple request.\n3. If it persists, check the provider's status page for an outage.\n4. Contact the API provider's support with the time and request details.",
        "prevention": "You can't fix the server, but you CAN handle it gracefully: add retries and a friendly fallback message for your users.",
    },
    502: {
        "category": "Bad Gateway",
        "severity": "Server Error",
        "meaning": "A server acting as a gateway got an invalid response upstream.",
        "root_cause": "One server in the chain got a bad reply from another. Usually a temporary infrastructure hiccup on the provider's side.",
        "fix": "1. Retry after a few seconds — these are often brief.\n2. Check the provider's status page for known issues.\n3. If it's constant, the provider likely has an outage — contact support.",
        "prevention": "Add automatic retries with backoff so short gateway blips don't reach your users.",
    },
    503: {
        "category": "Service Unavailable",
        "severity": "Server Error",
        "meaning": "The server is temporarily overloaded or down for maintenance.",
        "root_cause": "The service can't handle the request right now — too much traffic or planned maintenance.",
        "fix": "1. Wait and retry — check the 'Retry-After' header if present.\n2. Look at the provider's status page for maintenance notices.\n3. Use exponential backoff rather than retrying instantly in a loop.",
        "prevention": "Design your app to degrade gracefully when a dependency is down, and queue work to retry later.",
    },
    504: {
        "category": "Gateway Timeout",
        "severity": "Server Error",
        "meaning": "A gateway server didn't get a response in time from upstream.",
        "root_cause": "A server in the chain waited too long for another and gave up — usually an overloaded or slow upstream service.",
        "fix": "1. Retry after a short delay.\n2. If you control any part of the chain, look for the slow step.\n3. Check the provider's status page for performance issues.",
        "prevention": "Add retries with backoff and keep requests small so they complete well within time limits.",
    },
}


def analyze_error(status_code):
    """Look up a status code in our knowledge base and return the full details."""
    if status_code in KNOWLEDGE_BASE:
        return KNOWLEDGE_BASE[status_code]
    if 200 <= status_code < 300:
        return {"category": "Success", "severity": "OK",
                "meaning": "This is actually a success response — no error here!",
                "root_cause": "The request worked as intended.",
                "fix": "Nothing to fix — this status means success.",
                "prevention": "N/A"}
    elif 400 <= status_code < 500:
        return {"category": "Client Error (Generic)", "severity": "Client Error",
                "meaning": "A 4xx error — the problem is on the request/client side.",
                "root_cause": "Something about the request was rejected by the server.",
                "fix": "Review your URL, headers, and request body against the API docs. Read the response body for a specific message.",
                "prevention": "Validate requests before sending and follow the docs closely."}
    elif 500 <= status_code < 600:
        return {"category": "Server Error (Generic)", "severity": "Server Error",
                "meaning": "A 5xx error — the problem is on the server side.",
                "root_cause": "The server failed to handle the request, likely not your fault.",
                "fix": "Retry after a short wait and check the provider's status page. Contact their support if it persists.",
                "prevention": "Add retries and graceful fallbacks for server-side failures."}
    else:
        return {"category": "Unknown", "severity": "Unknown",
                "meaning": "This status code is outside the normal ranges.",
                "root_cause": "Unrecognized status code.",
                "fix": "Check the API documentation for what this code means.",
                "prevention": "N/A"}


# ----------------------------------------------------------------------------
#  THE USER INTERFACE
# ----------------------------------------------------------------------------
st.title("🔧 Smart API Error Detector")
st.caption("Detect what went wrong with an API call — and get a suggested fix.")
st.divider()

with st.expander("ℹ️  How it works"):
    st.markdown(
        """
        **Instant detection (Rules):** We read the HTTP status code and instantly
        classify the error type. This is deterministic — always correct for known
        codes, and it needs no internet or external service.

        **Expert fix suggestions (Knowledge base):** For each error we provide a
        detailed root cause, a concrete fix with examples, and a prevention tip,
        drawn from a built-in knowledge base of common API failures.

        The result is fast, reliable, and works entirely offline.
        """
    )

st.divider()

SAMPLES = {
    "-- Choose an example --": None,
    "🔒 401 Auth failure": {"status": 401, "endpoint": "https://api.example.com/v1/users", "method": "GET", "request_body": '{ "headers": { "Authorization": "" } }', "response_body": '{ "error": "Invalid API key provided" }'},
    "⏳ 429 Rate limit": {"status": 429, "endpoint": "https://api.example.com/v1/search", "method": "GET", "request_body": "(sent 500 requests in 10 seconds)", "response_body": '{ "error": "Too many requests. Retry after 30s." }'},
    "🔍 404 Not found": {"status": 404, "endpoint": "https://api.example.com/v1/user/9999", "method": "GET", "request_body": "(no body)", "response_body": '{ "error": "User with id 9999 does not exist" }'},
    "💥 500 Server error": {"status": 500, "endpoint": "https://api.example.com/v1/orders", "method": "POST", "request_body": '{ "item": "book", "qty": 2 }', "response_body": '{ "error": "Internal server error" }'},
    "📝 400 Bad request": {"status": 400, "endpoint": "https://api.example.com/v1/signup", "method": "POST", "request_body": '{ "email": "not-an-email", "age": "twenty" }', "response_body": '{ "error": "Invalid email format; age must be a number" }'},
}

chosen_sample = st.selectbox("Try a sample error (optional):", list(SAMPLES.keys()))

prefill = SAMPLES[chosen_sample] if SAMPLES[chosen_sample] else {"status": 400, "endpoint": "", "method": "GET", "request_body": "", "response_body": ""}

st.divider()
st.subheader("Enter the failed API call")

col1, col2 = st.columns(2)
with col1:
    status_code = st.number_input("HTTP Status Code", min_value=100, max_value=599, value=prefill["status"], help="The number returned by the API, e.g. 401, 404, 500")
with col2:
    method = st.selectbox("HTTP Method", ["GET", "POST", "PUT", "DELETE", "PATCH"], index=["GET", "POST", "PUT", "DELETE", "PATCH"].index(prefill["method"]))

endpoint = st.text_input("Endpoint (URL)", value=prefill["endpoint"], placeholder="https://api.example.com/v1/resource")
request_body = st.text_area("Request Body / What you sent", value=prefill["request_body"], placeholder='e.g. { "email": "test@test.com" }', height=100)
response_body = st.text_area("Response Body / The error message you got back", value=prefill["response_body"], placeholder='e.g. { "error": "Invalid API key" }', height=100)

if st.button("🔎 Analyze Error", type="primary", use_container_width=True):
    result = analyze_error(int(status_code))

    st.divider()
    st.subheader("🧩 Detection Result")
    if result["severity"] == "Server Error":
        st.error(f"**{result['category']}**  —  {result['severity']}")
    elif result["severity"] == "Client Error":
        st.warning(f"**{result['category']}**  —  {result['severity']}")
    elif result["severity"] == "OK":
        st.success(f"**{result['category']}**  —  {result['severity']}")
    else:
        st.info(f"**{result['category']}**  —  {result['severity']}")
    st.write(result["meaning"])

    st.divider()
    st.subheader("💡 Root Cause")
    st.write(result["root_cause"])

    st.subheader("🔧 How to Fix")
    st.code(result["fix"], language="text")

    st.subheader("🛡️ Prevention Tip")
    st.info(result["prevention"])

    if response_body and response_body.strip():
        with st.expander("📄 The response you provided"):
            st.code(response_body, language="json")

st.divider()
st.caption("Built for the Cognizant Hackathon • Instant detection + expert fix suggestions")
