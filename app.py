import streamlit as st
import pytesseract
from PIL import Image
import tempfile
import fitz  # PyMuPDF
from openai import OpenAI
from fpdf import FPDF

st.set_page_config(page_title="Médiscope", layout="wide")

if "syntheses" not in st.session_state:
    st.session_state["syntheses"] = []

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
Médiscope automatise l’analyse de dossiers médicaux pour produire une synthèse claire, directement prête à être transmise à l’assurance.
</p>
</div>
""", unsafe_allow_html=True)

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
    prompt = "Voici plusieurs synthèses médicales extraites d’un dossier complet :\n\n"
    for i, s in enumerate(syntheses):
        prompt += f"Synthèse {i+1}:\n{s}\n\n"
    prompt += "\nRédige une synthèse médico-légale consolidée, rigoureuse et unique selon le même plan habituel."

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

st.markdown('<div class="step">Étape 1 – Déposez un document médical (un par un)</div>', unsafe_allow_html=True)
file = st.file_uploader("📁 Formats acceptés : PDF, JPG, PNG", type=["pdf", "jpg", "jpeg", "png"])

if file:
    with st.spinner("🧠 Extraction du contenu..."):
        if file.type in ["image/jpeg", "image/png"]:
            extracted_text = extract_text_from_image(file)
        elif file.type == "application/pdf":
            extracted_text = extract_text_from_pdf(file)
        else:
            st.warning(f"Format non supporté : {file.name}")
            extracted_text = ""

    missing_fields = check_infos(extracted_text)
    st.markdown('<div class="step">Étape 2 – Aperçu du texte extrait</div>', unsafe_allow_html=True)
    st.text_area("Texte extrait", extracted_text, height=200)

    if missing_fields:
        st.warning(f"Informations manquantes : {', '.join(missing_fields)}")
        st.info("La synthèse IA indiquera explicitement les champs absents sans les inventer.")

    st.markdown('<div class="step">Étape 3 – Générer une synthèse pour ce document</div>', unsafe_allow_html=True)
    if st.button("🧬 Générer la synthèse de ce document"):
        with st.spinner("🧬 Synthèse en cours..."):
            synthesis = generate_structured_synthesis_safe(extracted_text, missing_fields)
            st.session_state.syntheses.append(synthesis)
            st.success("Synthèse ajoutée à la synthèse finale")
            st.text_area("🖊️ Synthèse générée (modifiable manuellement avant fusion)", synthesis, height=400)

if st.session_state.syntheses:
    st.markdown('<div class="step">Étape 4 – Fusionner toutes les synthèses ajoutées</div>', unsafe_allow_html=True)
    if st.button("🧩 Générer la synthèse globale finale"):
        with st.spinner("🔗 Fusion des synthèses..."):
            final_summary = generate_final_summary(st.session_state.syntheses)
            st.success("✅ Synthèse finale consolidée générée")
            edited = st.text_area("🖊️ Modifier la synthèse consolidée", final_summary, height=500)
            if st.button("📤 Exporter la synthèse PDF consolidée"):
                pdf_path = export_to_pdf(edited)
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 Télécharger la synthèse PDF", f, file_name="synthese_medicale_globale.pdf")

st.markdown('<div class="footer">© 2025 Médiscope · Version MVP – Ne pas diffuser sans accord</div>', unsafe_allow_html=True)
