import streamlit as st
import pytesseract
from PIL import Image
import tempfile
import fitz  # PyMuPDF
from openai import OpenAI
from fpdf import FPDF

st.set_page_config(page_title="Médiscope", layout="wide")

if "docs" not in st.session_state:
    st.session_state["docs"] = []
if "syntheses" not in st.session_state:
    st.session_state["syntheses"] = []

st.title("Médiscope – Analyse progressive de documents médicaux")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def extract_text_from_image(image_file):
    image = Image.open(image_file)
    return pytesseract.image_to_string(image, lang='fra', config='--psm 6')

def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = "\n".join([page.get_text() for page in doc])
    return text

def check_infos(text: str) -> list:
    required_fields = {
        "Nom": ["nom", "patient", "monsieur", "madame"],
        "Date de naissance": ["né le", "date de naissance"],
        "Date de l’accident": ["accident", "avp", "traumatisme", "collision"],
        "Examen clinique": ["examen clinique", "amplitude", "épaule", "rachis", "rotation"],
        "Traitement suivi": ["kinésithérapie", "immobilisation", "orthèse", "médicament"],
        "Date de consolidation": ["consolidation", "reprise", "stabilisation"],
        "DFP": ["déficit fonctionnel", "DFP", "%"],
        "Souffrances endurées": ["souffrances", "SE", "sur 7"],
        "Profession": ["profession", "travail", "carreleur", "activité professionnelle"],
    }
    missing_fields = []
    text_lower = text.lower()
    for label, keywords in required_fields.items():
        if not any(keyword in text_lower for keyword in keywords):
            missing_fields.append(label)
    return missing_fields

def generate_structured_synthesis_safe(text, missing_fields):
    max_input_length = 8000
    if len(text) > max_input_length:
        text = text[:max_input_length]
        st.warning("Le texte a été tronqué pour rester dans les limites de GPT-4.")

    liste_champs = ", ".join(missing_fields)
    infos_text = f"Informations absentes ou incomplètes : {liste_champs if missing_fields else 'aucune'}."

    prompt = f"""
Tu es un médecin expert en dommage corporel.

Voici un extrait de dossier médical à analyser :

{text}

---

{infos_text}

Si certaines données sont absentes, ne les invente jamais. Mentionne explicitement "Information absente du dossier" ou "À rechercher" dans la section concernée.

Rédige un rapport médico-légal structuré selon ce plan :

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
11. Conclusion médico-légale : 
    - Date de l'accident
    - Lésions identifiées
    - Date de consolidation
    - Gènes temporaires
    - Assistance par tierce personne
    - DFP (%)
    - SE (/7)
    - Pénibilité
    - Dommages esthétiques / d’agrément

Tu dois être rigoureux, synthétique, factuel et ne jamais supposer des éléments non présents.
Réponds en français.
"""

    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    output = response.choices[0].message.content
    estimated_tokens = len(prompt) // 4 + len(output) // 4
    estimated_cost = (estimated_tokens / 1000) * 0.04
    st.caption(f"Coût estimé de cette synthèse : {estimated_cost:.3f} $")
    return output

def generate_final_summary(syntheses):
    prompt = "Voici plusieurs synthèses médicales issues d’un même dossier :\n\n"
    for i, s in enumerate(syntheses):
        prompt += f"Synthèse {i+1}:\n{s}\n\n"
    prompt += "\nRédige une synthèse médico-légale globale et cohérente selon le même plan."

    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
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

st.header("Étape 1 – Déposer un document à la fois")
file = st.file_uploader("📁 Charger un fichier (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"])

if file and st.button("Analyser ce document"):
    with st.spinner("📄 Analyse du document en cours..."):
        if file.type in ["image/jpeg", "image/png"]:
            text = extract_text_from_image(file)
        elif file.type == "application/pdf":
            text = extract_text_from_pdf(file)
        else:
            st.warning("Format non supporté.")
            text = ""

        if text:
            missing = check_infos(text)
            synth = generate_structured_synthesis_safe(text, missing)
            st.session_state.docs.append(file.name)
            st.session_state.syntheses.append(synth)
            st.success(f"Synthèse ajoutée pour {file.name}")
            st.text_area(f"Synthèse générée ({file.name})", synth, height=300)

if st.session_state.syntheses:
    st.header("Étape 2 – Fusionner toutes les synthèses")
    if st.button("🧩 Générer la synthèse médico-légale finale"):
        with st.spinner("Fusion des synthèses en cours..."):
            final_report = generate_final_summary(st.session_state.syntheses)
            st.success("Synthèse finale générée !")
            edited = st.text_area("🖊️ Modifier la synthèse finale", final_report, height=500)
            if st.button("📥 Exporter en PDF"):
                pdf_path = export_to_pdf(edited)
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 Télécharger la synthèse PDF", f, file_name="synthese_finale.pdf")
