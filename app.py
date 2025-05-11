# Médiscope – Agent IA du médecin conseil (MVP)

import streamlit as st
import pytesseract
from PIL import Image
import tempfile
import fitz  # PyMuPDF
import openai
from fpdf import FPDF

# CONFIG
st.set_page_config(page_title="Médiscope", layout="wide")

# Clé API OpenAI
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- FONCTIONS ---

def extract_text_from_image(image_file):
    image = Image.open(image_file)
    return pytesseract.image_to_string(image, lang='fra')

def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = "\n".join([page.get_text() for page in doc])
    return text

def generate_synthesis(text):
    prompt = f"""
    Tu es un médecin conseil. Voici un dossier médical brut :
    {text}

    Résume ce dossier en 4 blocs :
    1. Antécédents médicaux
    2. Diagnostic actuel
    3. Traitements en cours
    4. Points de surveillance et recommandations

    Format clair, structuré, en français, sans interprétation juridique.
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    return response.choices[0].message.content

def export_to_pdf(synthesis):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in synthesis.split("\n"):
        pdf.multi_cell(0, 10, txt=line)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)
    return temp.name

# --- INTERFACE ---

st.title("🧠 Médiscope – Agent IA du médecin conseil")
file = st.file_uploader("📁 Téléversez un dossier médical (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"])

if file:
    with st.spinner("🔍 Analyse du document..."):
        if file.type in ["image/jpeg", "image/png"]:
            raw_text = extract_text_from_image(file)
        elif file.type == "application/pdf":
            raw_text = extract_text_from_pdf(file)
        else:
            st.error("❌ Format non supporté pour l’instant.")
            st.stop()

    st.subheader("📄 Texte extrait")
    st.text_area("Texte brut", raw_text, height=200)

    if st.button("🧬 Générer la synthèse IA"):
        with st.spinner("🤖 Synthèse en cours..."):
            synthesis = generate_synthesis(raw_text)
            st.subheader("🧾 Synthèse médicale IA")
            edited = st.text_area("🖊️ Modifier la synthèse", synthesis, height=400)

            if st.button("📤 Exporter en PDF"):
                pdf_path = export_to_pdf(edited)
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 Télécharger le PDF", f, file_name="synthese_medicale.pdf")

        st.success("✅ Synthèse générée avec succès !")
