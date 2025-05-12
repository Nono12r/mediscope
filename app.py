# Médiscope – Agent IA du médecin conseil (multi-documents)

import streamlit as st
import pytesseract
from PIL import Image
import tempfile
import fitz  # PyMuPDF
from openai import OpenAI
from fpdf import FPDF

# CONFIG
st.set_page_config(page_title="Médiscope", layout="wide")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- FONCTIONS ---

def extract_text_from_image(image_file):
    image = Image.open(image_file)
    return pytesseract.image_to_string(image, lang='fra')

def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = "\n".join([page.get_text() for page in doc])
    return text

def generate_structured_synthesis(text):
    prompt = f"""
    Tu es un médecin conseil expert. Voici un ensemble de documents médicaux bruts :
    {text}

    Rédige une synthèse médico-légale structurée destinée à une compagnie d’assurance.
    Le rapport doit comporter les sections suivantes :

    1. Informations générales du patient
    2. Rappel des faits et déroulement
    3. Retentissement personnel et professionnel
    4. Doléances
    5. Traitements en cours
    6. Examen clinique
    7. Discussion médico-légale
    8. Conclusion (type
