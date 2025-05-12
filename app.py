import streamlit as st
import pytesseract
from PIL import Image
import tempfile
import fitz  # PyMuPDF
from openai import OpenAI
from fpdf import FPDF

st.set_page_config(page_title="Médiscope", layout="wide")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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
        model="gpt-4o",
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

st.title("🧠 Médiscope – Agent IA du médecin conseil")
files = st.file_uploader("📁 Téléversez un ou plusieurs documents médicaux (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)

if files:
    all_texts = []
    with st.spinner("🔍 Extraction des contenus..."):
        for file in files:
            if file.type in ["image/jpeg", "image/png"]:
                all_texts.append(extract_text_from_image(file))
            elif file.type == "application/pdf":
                all_texts.append(extract_text_from_pdf(file))
            else:
                st.warning(f"Format non supporté : {file.name}")

    combined_text = "\n\n".join(all_texts)

    st.subheader("📄 Aperçu du texte extrait")
    st.text_area("Texte combiné extrait des documents", combined_text, height=200)

    if st.button("🧬 Générer la synthèse IA consolidée"):
        with st.spinner("🤖 Synthèse en cours..."):
            synthesis = generate_structured_synthesis(combined_text)
            st.subheader("🧾 Synthèse médicale IA")
            edited = st.text_area("🖊️ Modifier la synthèse", synthesis, height=500)

            if st.button("📤 Exporter en PDF"):
                pdf_path = export_to_pdf(edited)
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 Télécharger la synthèse PDF", f, file_name="synthese_medicale.pdf")

        st.success("✅ Synthèse générée avec succès !")
