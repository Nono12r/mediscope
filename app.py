import streamlit as st
import pytesseract
from PIL import Image
import tempfile
import fitz  # PyMuPDF
from openai import OpenAI
from fpdf import FPDF

st.set_page_config(page_title="Médiscope", layout="wide")

# 💡 Style CSS pro
st.markdown("""
    <style>
        body { background-color: #F1FAEF; font-family: 'Inter', sans-serif; }
        .title { font-size: 36px; color: #1D3557; font-weight: bold; margin-bottom: 0px; }
        .claim { font-size: 18px; color: #84A98C; margin-top: 0px; }
        .step { font-size: 20px; color: #1D3557; margin-top: 30px; font-weight: bold; }
        .small-text { font-size: 13px; color: gray; }
        .footer { font-size: 12px; color: #999; text-align: center; margin-top: 50px; }
        .stButton > button { background-color: #A8DADC; color: black; border-radius: 5px; padding: 10px 20px; border: none; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Logo et titre
st.image("logo_mediscope.png", width=160)
st.markdown('<div class="title">Médiscope</div>', unsafe_allow_html=True)

# Claim
st.markdown("""
<div class="claim">
<p style="font-size: 20px; color: #1D3557; font-weight: 600; margin-bottom: 0;">
Gagnez du temps dans l’analyse des dossiers, concentrez-vous sur l’essentiel : vos patients.
</p>
<p style="font-size: 16px; color: #555; margin-top: 5px;">
Médiscope automatise l’analyse de dossiers médicaux pour produire une synthèse claire, directement prête à être transmise à l’assurance. Il vous libère du tri et de la lecture fastidieuse des documents, tout en fiabilisant sa démarche.
</p>
</div>
""", unsafe_allow_html=True)

# Proposition de valeur
st.markdown("""
<div style="margin-top: 30px; background-color: #FFFFFF; padding: 20px; border-radius: 8px; border: 1px solid #E0E0E0;">
    <h4 style="color: #1D3557; margin-bottom: 10px;">Un outil conçu pour les médecins conseils, pensé pour :</h4>
    <ul style="color: #333; font-size: 16px; line-height: 1.6;">
        <li><strong>⚡ Réduire de 50 à 70 %</strong> le temps d’analyse des dossiers.</li>
        <li><strong>🧾 Fournir une synthèse claire, standardisée, exportable à l’assurance.</strong></li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Authentification à l'API
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Fonctions ---

def extract_text_from_image(image_file):
    image = Image.open(image_file)
    return pytesseract.image_to_string(image, lang='fra')

def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = "\n".join([page.get_text() for page in doc])
    return text

def generate_structured_synthesis(text):
    prompt = (
        f"Tu es un médecin conseil expert. Voici un ensemble de documents médicaux bruts :\n"
        f"{text}\n\n"
        "Rédige une synthèse médico-légale structurée destinée à une compagnie d’assurance.\n"
        "Le rapport doit comporter les sections suivantes :\n"
        "1. Informations générales du patient\n"
        "2. Rappel des faits et déroulement\n"
        "3. Retentissement personnel et professionnel\n"
        "4. Doléances\n"
        "5. Traitements en cours\n"
        "6. Examen clinique\n"
        "7. Discussion médico-légale\n"
        "8. Conclusion (type : date accident, lésions, gêne, consolidation, DFP, SE, pénibilité, etc.)\n\n"
        "Le ton doit être formel, précis, synthétique. Utilise des paragraphes courts et numérotés si nécessaire.\n"
        "Réponds en français."
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
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

# --- Interface utilisateur ---

st.markdown('<div class="step">Étape 1 – Déposez vos documents médicaux</div>', unsafe_allow_html=True)
files = st.file_uploader("📁 Formats acceptés : PDF, JPG, PNG", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)

if files:
    all_texts = []
    with st.spinner("🧠 Analyse en cours..."):
        for file in files:
            if file.type in ["image/jpeg", "image/png"]:
                all_texts.append(extract_text_from_image(file))
            elif file.type == "application/pdf":
                all_texts.append(extract_text_from_pdf(file))
            else:
                st.warning(f"Format non supporté : {file.name}")

    combined_text = "\n\n".join(all_texts)

    st.markdown('<div class="step">Étape 2 – Aperçu du texte extrait</div>', unsafe_allow_html=True)
    st.text_area("Texte combiné extrait des documents", combined_text, height=200)

    st.markdown('<div class="step">Étape 3 – Générer la synthèse IA</div>', unsafe_allow_html=True)
    if st.button("🧬 Générer la synthèse IA consolidée"):
        with st.spinner("🧬 Génération en cours..."):
            synthesis = generate_structured_synthesis(combined_text)
            st.success("✅ Synthèse générée avec succès !")

            st.markdown('<div class="step">Étape 4 – Modifier ou exporter</div>', unsafe_allow_html=True)
            edited = st.text_area("🖊️ Modifier la synthèse", synthesis, height=500)

            if st.button("📤 Exporter en PDF"):
                pdf_path = export_to_pdf(edited)
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 Télécharger la synthèse PDF", f, file_name="synthese_medicale.pdf")

# Footer
st.markdown('<div class="footer">© 2025 Médiscope · Version MVP · Produit en test – ne pas diffuser sans accord</div>', unsafe_allow_html=True)
