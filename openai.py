import streamlit as st
import google.generativeai as genai
import os
import requests
from dotenv import load_dotenv
from docx import Document
import pdfplumber
from gtts import gTTS
import tempfile
import time
from streamlit_mic_recorder import speech_to_text

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")
HF_API_KEY = os.getenv("HF_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Page setup
st.set_page_config(page_title="CAREER COUNSELLOR👩🏻‍🎓", layout="centered")
st.title("🎓 Pathfinder")
st.markdown("This chatbot answers only career/job/college-related queries. Avoid using it for emergencies.")

# System prompt
DOMAIN_PROMPT = (
    "You are a helpful and knowledgeable career/job/college counselling specialist. "
    "Only respond to career/job/college questions. If a question is outside the career/job/college domain, politely refuse to answer."
)

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Resume Upload + Hugging Face Analysis ---
def extract_text_from_docx(uploaded_file):
    doc = Document(uploaded_file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_pdf(uploaded_file):
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        return text
    except Exception as e:
        return f"❌ Failed to read PDF: {e}"

def analyze_resume_with_huggingface(text):
    API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    candidate_labels = [
        "Software Engineer", "Data Scientist", "Graphic Designer",
        "Teacher", "Business Analyst", "Product Manager", "UX Designer"
    ]
    payload = {
        "inputs": text,
        "parameters": {"candidate_labels": candidate_labels}
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

st.sidebar.markdown("### 📄 Resume Analysis")
uploaded_file = st.sidebar.file_uploader("Upload Resume (.docx or .pdf)", type=["docx", "pdf"])

resume_text = ""
if uploaded_file:
    if uploaded_file.name.endswith(".docx"):
        resume_text = extract_text_from_docx(uploaded_file)
    elif uploaded_file.name.endswith(".pdf"):
        resume_text = extract_text_from_pdf(uploaded_file)

if resume_text:
    st.sidebar.text_area("Extracted Resume Text", resume_text[:3000], height=150)

    if st.sidebar.button("Analyze Resume"):
        with st.spinner("Analyzing your resume..."):
            result = analyze_resume_with_huggingface(resume_text)
            if "labels" in result:
                st.success("🔍 Career Roles Predicted:")
                for label, score in zip(result["labels"], result["scores"]):
                    st.markdown(f"- **{label}**: {score*100:.2f}%")
            else:
                st.error(f"❌ Failed to analyze resume.\n{result.get('error', 'Unknown error')}")

# --- 🎙️ Voice Input ---
st.sidebar.markdown("### 🎙️ Speak to Ask")
voice_input = speech_to_text(
    language='en',
    start_prompt="🎤 Start speaking",
    stop_prompt="⏹️ Stop",
    just_once=True,
    key='STT'
) or ""

if voice_input:
    st.sidebar.success(f"You said: {voice_input}")

# --- Job Search Function ---
def search_jobs(query, location="India"):
    url = f"https://{RAPIDAPI_HOST}/search"
    params = {"query": query, "location": location, "page": "1", "num_pages": "1"}
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        jobs = response.json().get("data", [])
        if not jobs:
            return "🔍 No jobs found for this query."
        job_list = "\n\n".join(
            [f"**{job['job_title']}** at {job['employer_name']}\n📍 {job['job_city']}, {job['job_country']}\n🔗 [Apply Here]({job['job_apply_link']})"
             for job in jobs[:5]]
        )
        return f"Here are some job openings:\n\n{job_list}"
    except Exception as e:
        return f"⚠ Failed to fetch jobs: {e}"

# ✅ Fixed TTS function with safe cleanup
def speak_text(text):
    tts = gTTS(text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        temp_file = fp.name
        tts.save(temp_file)

    st.audio(temp_file, format='audio/mp3')

    time.sleep(3)  # Wait to allow Streamlit to play it
    try:
        os.remove(temp_file)
    except PermissionError:
        pass

# --- Chat Input (Text or Voice) ---
text_input = st.chat_input("Enter your career-related question here...")
user_input = voice_input or text_input

if user_input:
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    chat_history = "\n".join(
        [f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.messages]
    )
    full_prompt = f"{DOMAIN_PROMPT}\n\n{chat_history}\nUser: {user_input}"

    # Job search detection
    job_keywords = ["job", "jobs", "openings", "opportunity", "vacancy"]
    search_keywords = ["find", "search", "looking", "get", "apply"]
    if any(jk in user_input.lower() for jk in job_keywords) and any(sk in user_input.lower() for sk in search_keywords):
        bot_reply = search_jobs(user_input)
    else:
        try:
            response = model.generate_content(full_prompt)
            bot_reply = response.text
        except Exception as e:
            bot_reply = f"⚠ Error: {e}"

    st.chat_message("assistant", avatar="OIP.webp").markdown(bot_reply)
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})

     


