import streamlit as st
import pytesseract
from PIL import Image
import tempfile
import fitz
from openai import OpenAI
from fpdf import FPDF
import io

st.set_page_config(page_title="Médiscope", layout="wide")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "syntheses" not in st.session_state:
    st.session_state.syntheses = []
if "documents" not in st.session_state:
    st.session_state.documents = []
if "final_synthesis" not in st.session_state:
    st.session_state.final_synthesis = None

st.title("🩺 Médiscope – Analyse médico-légale progressive")

st.markdown("""
Bienvenue dans l’interface Médiscope. Déposez vos documents médicaux **un par un**, obtenez une **synthèse médicale experte à chaque étape**, puis fusionnez-les en un **rapport final structuré**.
""")

# Extraction OCR ou texte direct
def extract_text(file):
    if file.type.startswith("image"):
        image = Image.open(file)
        text = pytesseract.image_to_string(image, lang='fra', config='--psm 6')
        return text + "\n[Source : image analysée par OCR]"

    elif file.type == "application/pdf":
        doc = fitz.open(stream=file.read(), filetype="pdf")
        full_text = ""
        for page_number, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                full_text += f"\n--- Page {page_number+1} : texte direct ---\n{text}\n"
            else:
                pix = page.get_pixmap(dpi=300)
                image_bytes = io.BytesIO(pix.tobytes("png"))
                image = Image.open(image_bytes)
                ocr_text = pytesseract.image_to_string(image, lang='fra', config='--psm 6')
                full_text += f"\n--- Page {page_number+1} : texte OCR ---\n{ocr_text}\n"
        return full_text.strip()

    else:
        return "[Format non supporté ou erreur d'ouverture du fichier]"


# Synthèse IA segmentée
def generate_structured_synthesis(text):
    prompt = f"""
Tu es un médecin expert en dommage corporel. Voici un extrait de dossier médical à analyser :

{text}

Rédige une synthèse médico-légale structurée selon le plan suivant :
1. Informations personnelles
2. Mission et contexte
3. État antérieur
4. Rappel chronologique des faits
5. Traitements suivis
6. Retentissement personnel
7. Retentissement professionnel
8. Doléances actuelles
9. Examen clinique
10. Discussion médico-légale
11. Conclusion médico-légale

Mentionne explicitement les informations absentes. Sois rigoureux, structuré et professionnel.
Réponds en français.
"""
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content

# Fusion finale des synthèses
def generate_final_synthesis(syntheses):
    prompt = "Voici plusieurs synthèses médicales individuelles issues d’un dossier complet :\n\n"
    for i, s in enumerate(syntheses):
        prompt += f"Synthèse {i+1} :\n{s}\n\n"
    prompt += "\nRédige une synthèse médico-légale unique, rigoureuse, cohérente, selon le plan habituel."

    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content

# Export PDF
def export_to_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text.split("\n"):
        pdf.multi_cell(0, 10, line)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)
    return temp.name

st.header("Étape en cours – Déposez un nouveau document médical")
file = st.file_uploader("📁 Ajouter un document (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"])

if file and st.button("Analyser ce document"):
    with st.spinner("🔍 Lecture et extraction en cours..."):
        text = extract_text(file)
        if text.strip():
            synthesis = generate_structured_synthesis(text)
            st.session_state.documents.append(file.name)
            st.session_state.syntheses.append(synthesis)
            st.success(f"✅ Synthèse générée pour {file.name}")
            st.text_area(f"📝 Synthèse du document : {file.name}", synthesis, height=350)
        else:
            st.error("❌ Impossible d'extraire du texte depuis ce document.")

# Liste des synthèses générées
if st.session_state.syntheses:
    st.header("📚 Synthèses générées")
    for i, synth in enumerate(st.session_state.syntheses):
        st.text_area(f"Synthèse {i+1} – {st.session_state.documents[i]}", synth, height=300)

    # Fusion finale
    st.header("🧩 Étape finale – Générer le rapport consolidé")
    if st.button("Fusionner toutes les synthèses"):
        with st.spinner("Fusion intelligente des synthèses..."):
            final = generate_final_synthesis(st.session_state.syntheses)
            st.session_state.final_synthesis = final
            st.success("✅ Rapport final prêt")

    if st.session_state.final_synthesis:
        st.text_area("🖊️ Modifier la synthèse finale consolidée", st.session_state.final_synthesis, height=500)
        if st.button("📤 Télécharger le rapport final en PDF"):
            pdf_path = export_to_pdf(st.session_state.final_synthesis)
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Télécharger le PDF", f, file_name="synthese_medico_legale_finale.pdf")
