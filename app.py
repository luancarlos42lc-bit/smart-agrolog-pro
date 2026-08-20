import streamlit as st
import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO
from fpdf import FPDF
import tempfile
import os

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="AgroVision - Inteligência Artificial para Cana-de-Açúcar",
    page_icon="🌾",
    layout="wide"
)


# ---------------------------------------------------------
# CARREGAMENTO DO MODELO YOLO
# ---------------------------------------------------------
@st.cache_resource
def load_model():
    # Carrega o modelo treinado (assegure-se de que best.pt está na raiz do projeto)
    return YOLO("best.pt")


model = load_model()

# ---------------------------------------------------------
# DICIONÁRIO DE DIAGNÓSTICOS E MANEJO
# ---------------------------------------------------------
DIAGNOSTICOS = {
    "Ferrugem": {
        "causa": "Fungo Puccinia melanocephala",
        "sintomas": "Pústulas alongadas de cor marrom-alaranjada nas folhas.",
        "recomendacao": "Aplicação de fungicidas sistêmicos e uso de variedades resistentes."
    },
    "Carvao": {
        "causa": "Fungo Sporisorium scitamineum",
        "sintomas": "Estatura reduzida e surgimento do 'chicote' característico no topo do colmo.",
        "recomendacao": "Roliçamento (eliminação de plantas doentes) e desinfecção de mudas."
    },
    "Blight": {
        "causa": "Bactéria Xanthomonas albilineans / Queima-das-folhas",
        "sintomas": "Riscos esbranquiçados/amarelados paralelos às nervuras das folhas.",
        "recomendacao": "Utilizar mudas sadias de viveiro e higienizar facões de corte."
    },
    "Healthy": {
        "causa": "Planta Sadia",
        "sintomas": "Folhas de coloração verde homogênea sem presença de lesões.",
        "recomendacao": "Manter adubação equilibrada e monitoramento periódico de rotina."
    }
}


# ---------------------------------------------------------
# FUNÇÃO PARA GERAR PDF (FASE 1)
# ---------------------------------------------------------
def gerar_pdf(classe_detectada, confianca, imagem_pil):
    info = DIAGNOSTICOS.get(classe_detectada, {
        "causa": "Desconhecida",
        "sintomas": "Nenhum sintoma específico cadastrado.",
        "recomendacao": "Consultar um engenheiro agronômico."
    })

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)

    # Cabeçalho
    pdf.cell(0, 10, "AgroVision - Laudo de Diagnostico Agronomico", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, "Sistema de Monitoramento e Visao Computacional em Canaviais", ln=True, align='C')
    pdf.ln(10)

    # Dados do Diagnóstico
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Diagnostico Detectado: {classe_detectada}", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Precisao do Modelo (Confianca): {confianca:.1f}%", ln=True)
    pdf.cell(0, 8, f"Agente Causal: {info['causa']}", ln=True)
    pdf.ln(5)

    # Sintomas e Recomendação
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Sintomas Observados:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, info['sintomas'])
    pdf.ln(3)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Recomendacao Tecnica de Manejo:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, info['recomendacao'])
    pdf.ln(8)

    # Salvando Imagem temporária para o PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        imagem_pil.save(tmp.name)
        pdf.image(tmp.name, x=15, w=100)
        tmp_path = tmp.name

    pdf_output = pdf.output(dest='S').encode('latin1')
    os.remove(tmp_path)
    return pdf_output


# ---------------------------------------------------------
# BARRA LATERAL (NAVEGAÇÃO ENTRE FASES)
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/sugar-cane.png", width=80)
st.sidebar.title("AgroVision AI")
st.sidebar.markdown("Plataforma de Monitoramento Fitossanitário")

opcao_modulo = st.sidebar.radio(
    "Selecione o Módulo de Análise:",
    ("🔍 Visão Micro (Análise de Folha - Fase 1)", "🛰️ Visão Macro (Análise de Talhão/Drone - Fase 2)")
)

# ---------------------------------------------------------
# MÓDULO 1: VISÃO MICRO (ANALISE DE FOLHA)
# ---------------------------------------------------------
if opcao_modulo == "🔍 Visão Micro (Análise de Folha - Fase 1)":
    st.title("🌾 AgroVision - Análise Focal da Folha")
    st.markdown("Carregue uma imagem aproximada da folha para diagnóstico e emissão de laudo técnico.")

    uploaded_file = st.file_uploader("Escolha uma foto da folha...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image_pil = Image.open(uploaded_file).convert("RGB")
        col1, col2 = st.columns(2)

        with col1:
            st.image(image_pil, caption="Imagem Original", use_container_width=True)

        with st.spinner("Processando diagnóstico com a IA..."):
            results = model.predict(image_pil, conf=0.25)
            annotated_frame = results[0].plot()
            annotated_pil = Image.fromarray(annotated_frame[:, :, ::-1])

        with col2:
            st.image(annotated_pil, caption="Detecção de Anomalias", use_container_width=True)

        boxes = results[0].boxes
        if len(boxes) > 0:
            top_box = boxes[0]
            cls_id = int(top_box.cls[0])
            classe_detectada = model.names[cls_id]
            confianca = float(top_box.conf[0]) * 100

            st.success(f"**Diagnóstico:** {classe_detectada} ({confianca:.1f}% de confiança)")

            info = DIAGNOSTICOS.get(classe_detectada, {})
            if info:
                st.info(f"**Causa:** {info.get('causa')}\n\n**Recomendação:** {info.get('recomendacao')}")

            pdf_bytes = gerar_pdf(classe_detectada, confianca, annotated_pil)
            st.download_button(
                label="📄 Baixar Laudo Técnico em PDF",
                data=pdf_bytes,
                file_name=f"Laudo_AgroVision_{classe_detectada}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("Nenhuma anomalia evidente foi identificada pelo modelo de IA nesta foto.")

# ---------------------------------------------------------
# MÓDULO 2: VISÃO MACRO (Mapeamento de Talhão via Drone)
# ---------------------------------------------------------
else:
    st.title("🛰️ AgroVision - Monitoramento de Talhões via Drone")
    st.markdown(
        "Faça upload da imagem aérea/mosaico do talhão para varredura em grid e geração do **Mapa de Severidade**.")

    uploaded_drone = st.file_uploader("Escolha a foto aérea ou ortomosaico do talhão...", type=["jpg", "jpeg", "png"])

    if uploaded_drone is not None:
        image_drone = Image.open(uploaded_drone).convert("RGB")
        img_np = np.array(image_drone)

        st.subheader("1. Imagem Aérea do Talhão")
        st.image(image_drone, caption="Mosaico Aéreo Carregado", use_container_width=True)

        if st.button("🚀 Processar Varredura e Gerar Mapa de Calor"):
            with st.spinner("Realizando fatiamento em grid e varredura do canavial com IA..."):
                h, w, _ = img_np.shape
                grid_size = 320  # Tamanho do bloco do grid em pixels

                # Criar máscara para o mapa de calor (Overlay)
                heatmap_mask = np.zeros_like(img_np, dtype=np.uint8)

                total_quadros = 0
                quadros_infectados = 0

                # Algoritmo de Tiling (Fatiamento)
                for y in range(0, h, grid_size):
                    for x in range(0, w, grid_size):
                        # Garante que os limites não ultrapassem a imagem
                        y_end = min(y + grid_size, h)
                        x_end = min(x + grid_size, w)

                        crop = img_np[y:y_end, x:x_end]
                        if crop.shape[0] < 50 or crop.shape[1] < 50:
                            continue

                        total_quadros += 1

                        # Processa cada bloco com a IA
                        results = model.predict(crop, conf=0.20, verbose=False)
                        boxes = results[0].boxes

                        # Se encontrar qualquer anomalia no bloco
                        if len(boxes) > 0:
                            quadros_infectados += 1
                            # Pinta a área no overlay de VERMELHO (RGB: 255, 0, 0) para foco crítico
                            heatmap_mask[y:y_end, x:x_end] = [255, 0, 0]
                        else:
                            # Pinta a área no overlay de VERDE (RGB: 0, 255, 0) para saudável
                            heatmap_mask[y:y_end, x:x_end] = [0, 255, 0]

                # Aplicação de Alpha Blending (Sobreposição do Mapa de Calor com Transparência)
                alpha = 0.45  # Nível de transparência (45%)
                overlay_resultado = cv2.addWeighted(img_np, 1 - alpha, heatmap_mask, alpha, 0)

                # Cálculo do Índice de Infestação
                taxa_infestacao = (quadros_infectados / total_quadros * 100) if total_quadros > 0 else 0

                st.subheader("2. Resultado do Mapeamento de Severidade")

                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.image(overlay_resultado, caption="Mapa de Calor (Vermelho = Infecção / Verde = Limpo)",
                             use_container_width=True)

                with col_res2:
                    st.metric(label="📊 Taxa de Infestação do Talhão", value=f"{taxa_infestacao:.1f}%")
                    st.write(f"- **Total de Blocos Analisados:** {total_quadros}")
                    st.write(f"- **Blocos com Focos de Doença:** {quadros_infectados}")

                    if taxa_infestacao < 10:
                        st.success(
                            "✅ **Nível de Severidade: BAIXO**\nTalhão em ótimas condições sanidade. Manter apenas monitoramento.")
                    elif taxa_infestacao < 30:
                        st.warning(
                            "⚠️ **Nível de Severidade: MÉDIO**\nAtenção necessária nas zonas em vermelho. Recomenda-se aplicação focalizada.")
                    else:
                        st.error(
                            "🚨 **Nível de Severidade: CRÍTICO**\nAlta infestação detectada! Planejar aplicação imediata de defensivos via taxa variável.")