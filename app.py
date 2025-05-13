import streamlit as st
import tempfile
import fitz
import requests
from openai import OpenAI
from fpdf import FPDF
import io

st.set_page_config(page_title="Médiscope", layout="wide")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
OCR_API_KEY = st.secrets["OCR_SPACE_API_KEY"]

if "syntheses" not in st.session_state:
    st.session_state.syntheses = []
if "documents" not in st.session_state:
    st.session_state.documents = []
if "final_synthesis" not in st.session_state:
    st.session_state.final_synthesis = None

st.title("🩺 Médiscope – Analyse médico-légale progressive")

st.markdown("""
Bienvenue dans l’interface Médiscope. Déposez vos documents médicaux **un par un**, même scannés ou en plusieurs pages. Médiscope analysera chaque page individuellement et vous proposera une **synthèse complète et consolidée**.
""")

# 🔍 OCR Cloud via OCR.space
def ocr_via_ocrspace_bytes(byte_data, filename="page.png"):
    url = "https://api.ocr.space/parse/image"
    payload = {
        'language': 'fre',
        'isOverlayRequired': False,
        'OCREngine': 2,
    }
    files = {
        'file': (filename, byte_data, 'image/png')
    }
    headers = {
        'apikey': OCR_API_KEY
    }
    response = requests.post(url, data=payload, files=files, headers=headers)
    result = response.json()
    if result.get("IsErroredOnProcessing"):
        return "[Erreur OCR.space] " + result.get("ErrorMessage", ["Inconnue"])[0]
    else:
        return result["ParsedResults"][0]["ParsedText"]

# 🔄 Lecture intelligente PDF multi-pages
def extract_text(file):
    if file.type.startswith("image"):
        byte_data = file.read()
        return ocr_via_ocrspace_bytes(byte_data, filename=file.name)

    elif file.type == "application/pdf":
        doc = fitz.open(stream=file.read(), filetype="pdf")
        all_text = ""
        for page_number, page in enumerate(doc):
            pix = page.get_pixmap(dpi=300)
            image_bytes = io.BytesIO(pix.tobytes("png"))
            image_bytes.seek(0)
            page_text = ocr_via_ocrspace_bytes(image_bytes.read(), filename=f"page_{page_number+1}.png")
            all_text += f"\n--- Page {page_number+1} : OCR ---\n{page_text.strip()}\n"
        return all_text.strip()

    else:
        return "[Format non supporté ou erreur d'ouverture du fichier]"

# 🤖 Génération IA

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

# 🔗 Fusion des synthèses
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

# 📤 Export PDF
def export_to_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text.split("\n"):
        pdf.multi_cell(0, 10, line)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)
    return temp.name

# 📁 Interface de dépôt
temp_file = st.file_uploader("📁 Ajouter un document (PDF ou image JPG/PNG)", type=["pdf", "jpg", "jpeg", "png"])

if temp_file and st.button("Analyser ce document"):
    with st.spinner("🔍 Analyse OCR page par page..."):
        text = extract_text(temp_file)
        if text.strip():
            synthesis = generate_structured_synthesis(text)
            st.session_state.documents.append(temp_file.name)
            st.session_state.syntheses.append(synthesis)
            st.success(f"✅ Synthèse générée pour {temp_file.name}")
            st.text_area(f"📝 Synthèse du document : {temp_file.name}", synthesis, height=350)
        else:
            st.error("❌ Impossible d'extraire du texte depuis ce document.")

if st.session_state.syntheses:
    st.header("📚 Synthèses générées")
    for i, synth in enumerate(st.session_state.syntheses):
        st.text_area(f"Synthèse {i+1} – {st.session_state.documents[i]}", synth, height=300)

    st.header("🧩 Étape finale – Rapport consolidé")
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
