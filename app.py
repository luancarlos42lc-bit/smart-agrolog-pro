import streamlit as st
from ultralytics import YOLO
from PIL import Image
import cv2
import numpy as np
from datetime import datetime
from fpdf import FPDF
import tempfile
import os

# Configuração da página
st.set_page_config(page_title="AgroVision", page_icon="🌱", layout="wide")

st.title("🌱 AgroVision: Detecção e Manejo de Doenças na Cana")
st.write("Faça o upload de uma imagem para realizar a análise por Inteligência Artificial.")

# Dicionário de tradução
TRADUCOES = {
    "bacterialblight": "Mancha Bacteriana",
    "Bacterial Blight": "Mancha Bacteriana",
    "blacksmut": "Carvão",
    "Black Smut": "Carvão",
    "smut": "Carvão",
    "Smut": "Carvão",
    "diseases": "Outras Doenças",
    "grassyshoot": "Touceira de Fato",
    "Grassy Shoot": "Touceira de Fato",
    "healthy": "Saudável",
    "Healthy": "Saudável",
    "pokkahboeng": "Pokkah Boeng",
    "Pokkah Boeng": "Pokkah Boeng",
    "redrot": "Podridão Vermelha",
    "Red Rot": "Podridão Vermelha",
    "rust": "Ferrugem",
    "Rust": "Ferrugem",
    "yellowleaf": "Amarelo da Cana",
    "Yellow Leaf": "Amarelo da Cana"
}

# Base de conhecimento agronômico
RECOMENDACOES = {
    "Podridão Vermelha": {
        "causa": "Fungo Colletotrichum falcatum",
        "sintomas": "Lesoes avermelhadas na nervura central das folhas com manchas brancas no centro. Provoca secamento e apodrecimento dos tecidos.",
        "controle": "Uso de variedades resistentes, eliminacao de soqueiras doentes e controle da broca-da-cana."
    },
    "Ferrugem": {
        "causa": "Fungo Puccinia melanocephala ou Puccinia kuehnii",
        "sintomas": "Pustulas elongadas de cor marrom ou alaranjada na superficie das folhas, levando ao secamento precoce.",
        "controle": "Utilizacao de cultivares geneticamente resistentes e aplicacao de fungicidas registrados em focos severos."
    },
    "Carvão": {
        "causa": "Fungo Sporisorium scitamineum",
        "sintomas": "Aparecimento de uma estrutura em formato de chicote escuro no topo do colmo, enfezamento e perfilhamento excessivo.",
        "controle": "Roguing (eliminacao manual de plantas doentes antes da abertura do chicote), tratamento termico e variedades resistentes."
    },
    "Pokkah Boeng": {
        "causa": "Fungo Fusarium moniliforme",
        "sintomas": "Deformacao, rugosidade e enrugamento das folhas novas no topo da planta, com manchas avermelhadas.",
        "controle": "Geralmente a planta se recupera sozinha. Em casos graves, recomenda-se rotacao de cultura e uso de variedades menos suscetiveis."
    },
    "Amarelo da Cana": {
        "causa": "Fitoplasma ou Virus (SCYLV)",
        "sintomas": "Amarelecimento intenso da nervura central pelo lado inferior da folha, evoluindo para a lamina foliar.",
        "controle": "Uso de mudas sadias (livres do virus) e controle de pulgoes vetores."
    },
    "Saudável": {
        "causa": "Nenhuma anomalia detectada.",
        "sintomas": "Folhas com coloracao verde uniforme e tecidos preservados.",
        "controle": "Manter o plano de adubacao e monitoramento periodico do canavial."
    }
}


# Carregamento do Modelo
@st.cache_resource
def load_model():
    return YOLO("best.pt")


model = load_model()


# Função para desenhar boxes com texto em PT
def desenhar_boxes_pt(img_pil, boxes):
    img_cv = np.array(img_pil)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls_id = int(box.cls[0])
        raw_name = model.names[cls_id]
        conf = float(box.conf[0]) * 100

        nome_pt = TRADUCOES.get(raw_name, raw_name)
        label = f"{nome_pt} {conf:.1f}%"

        cv2.rectangle(img_cv, (x1, y1), (x2, y2), (0, 230, 115), 3)
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        y_label = max(y1, h + 10)
        cv2.rectangle(img_cv, (x1, y_label - h - 10), (x1 + w + 10, y_label + 5), (0, 230, 115), -1)
        cv2.putText(img_cv, label, (x1 + 5, y_label - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    return Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))


# Função para gerar o relatório PDF
def gerar_pdf(img_pil, detecções, lista_doencas):
    pdf = FPDF()
    pdf.add_page()

    # Cabeçalho
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(190, 10, "Relatorio de Diagnostico - AgroVision", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(190, 10, f"Data da Analise: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(5)

    # Salva imagem temporária para o PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        img_pil.save(tmp_file.name)
        tmp_path = tmp_file.name

    # Insere imagem
    pdf.image(tmp_path, x=45, w=120)
    pdf.ln(5)

    # Detecções
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(190, 10, "Resultados da IA:", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for det in detecções:
        pdf.cell(190, 7, f"- {det}", ln=True)

    pdf.ln(5)
    # Recomendações
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(190, 10, "Orientacoes Agronomicas:", ln=True)

    for doença in lista_doencas:
        info = RECOMENDACOES.get(doença, None)
        if info:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(190, 8, f"Doenca/Estado: {doença}", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(190, 6, f"Causa: {info['causa']}")
            pdf.multi_cell(190, 6, f"Sintomas: {info['sintomas']}")
            pdf.multi_cell(190, 6, f"Manejo Recomendado: {info['controle']}")
            pdf.ln(3)

    pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
    pdf.output(pdf_path)

    # Remove imagem temporária
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    return pdf_path


# Interface e Diagnóstico
uploaded_file = st.file_uploader("Selecione uma imagem de folha...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📷 Imagem Original")
        st.image(image)

    with col2:
        st.subheader("🔍 Diagnóstico da IA")
        if st.button("Analisar Folha"):
            results = model.predict(source=image, conf=0.40)
            boxes = results[0].boxes

            if len(boxes) > 0:
                img_processada = desenhar_boxes_pt(image, boxes)
                st.image(img_processada, caption="Detecção Processada (AgroVision)")
                st.success("Análise finalizada com sucesso!")

                doencas_detectadas = set()
                resumo_texto = []

                st.markdown("### 📋 Resumo das Detecções")
                for box in boxes:
                    cls_id = int(box.cls[0])
                    raw_name = model.names[cls_id]
                    conf = float(box.conf[0]) * 100
                    nome_pt = TRADUCOES.get(raw_name, raw_name)
                    doencas_detectadas.add(nome_pt)

                    texto_det = f"Doença/Estado: {nome_pt} ({conf:.1f}% de certeza)"
                    resumo_texto.append(texto_det)
                    st.write(f"• **{texto_det}**")

                st.markdown("---")
                st.markdown("### 💡 Orientações de Manejo Agronômico")

                for doença in doencas_detectadas:
                    info = RECOMENDACOES.get(doença, None)
                    if info:
                        with st.expander(f"📌 Plano de Ação: **{doença}**", expanded=True):
                            st.write(f"**Causa:** {info['causa']}")
                            st.write(f"**Sintomas:** {info['sintomas']}")
                            st.write(f"**Recomendação de Manejo:** {info['controle']}")

                # Gerar e disponibilizar o PDF para Download
                st.markdown("---")
                caminho_pdf = gerar_pdf(img_processada, resumo_texto, doencas_detectadas)
                with open(caminho_pdf, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Baixar Relatório em PDF",
                        data=pdf_file,
                        file_name=f"Relatorio_AgroVision_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf"
                    )
            else:
                st.warning("Nenhuma anomalia identificada com grau de certeza suficiente (confiança < 40%).")