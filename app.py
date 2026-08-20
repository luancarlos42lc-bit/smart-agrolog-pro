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
    "Rust": {
        "causa": "Fungo Puccinia melanocephala (Ferrugem da Cana)",
        "sintomas": "Pústulas alongadas de cor marrom-alaranjada nas folhas.",
        "recomendacao": "Aplicação de fungicidas sistêmicos e uso de variedades resistentes."
    },
    "Carvao": {
        "causa": "Fungo Sporisorium scitamineum",
        "sintomas": "Estatura reduzida e surgimento do 'chicote' característico no topo do colmo.",
        "recomendacao": "Roliçamento (eliminação de plantas doentes) e desinfecção de mudas."
    },
    "Smut": {
        "causa": "Fungo Sporisorium scitamineum (Carvão da Cana)",
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
# FUNÇÃO PARA GERAR PDF (MÓDULO 1)
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

    pdf_bytes = bytes(pdf.output())
    os.remove(tmp_path)
    return pdf_bytes


# ---------------------------------------------------------
# BARRA LATERAL (NAVEGAÇÃO ENTRE MÓDULOS)
# ---------------------------------------------------------
st.sidebar.title("🌾 AgroVision AI")
st.sidebar.markdown("Plataforma de Monitoramento Fitossanitário")

opcao_modulo = st.sidebar.radio(
    "Selecione o Módulo de Análise:",
    ("🔍 Visão Micro (Análise de Folha - Módulo 1)", "🛰️ Visão Macro (Análise de Talhão/Drone - Módulo 2)")
)

# ---------------------------------------------------------
# MÓDULO 1: VISÃO MICRO (ANÁLISE DE FOLHA)
# ---------------------------------------------------------
if opcao_modulo == "🔍 Visão Micro (Análise de Folha - Módulo 1)":
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
# MÓDULO 2: VISÃO MACRO (Mapeamento Térmico de Talhão via Drone)
# ---------------------------------------------------------
else:
    st.title("🛰️ AgroVision - Monitoramento de Talhões via Drone")
    st.markdown(
        "Faça upload da imagem aérea/mosaico do talhão para varredura e geração do **Mapa de Calor Térmico de Severidade**.")

    uploaded_drone = st.file_uploader("Escolha a foto aérea ou ortomosaico do talhão...", type=["jpg", "jpeg", "png"])

    if uploaded_drone is not None:
        image_drone = Image.open(uploaded_drone).convert("RGB")
        img_np = np.array(image_drone)

        st.subheader("1. Imagem Aérea do Talhão")
        st.image(image_drone, caption="Mosaico Aéreo Carregado", use_container_width=True)

        if st.button("🚀 Processar Varredura e Gerar Mapa de Calor"):
            with st.spinner("Analisando densidade foliar e gerando gradientes de severidade..."):
                h, w, _ = img_np.shape

                # Matriz de densidade de calor em ponto flutuante
                intensity_map = np.zeros((h, w), dtype=np.float32)

                # Configuração otimizada de varredura
                grid_size = max(40, min(int(w / 20), 200))
                conf_threshold = 0.15

                total_quadros = 0
                quadros_infectados = 0

                # Varredura em Grid (Fatiamento)
                for y in range(0, h, grid_size):
                    for x in range(0, w, grid_size):
                        y_end = min(y + grid_size, h)
                        x_end = min(x + grid_size, w)

                        crop = img_np[y:y_end, x:x_end]
                        if crop.shape[0] < 15 or crop.shape[1] < 15:
                            continue

                        total_quadros += 1

                        # Processamento via IA
                        results = model.predict(crop, conf=conf_threshold, verbose=False)
                        boxes = results[0].boxes

                        if len(boxes) > 0:
                            quadros_infectados += 1
                            # Acumula intensidade baseada no número de detecções
                            intensity_map[y:y_end, x:x_end] += len(boxes)

                taxa_infestacao = (quadros_infectados / total_quadros * 100) if total_quadros > 0 else 0

                # ---------------------------------------------------------
                # PROCESSAMENTO DO MAPA DE CALOR (INTERPOLAÇÃO TÉRMICA)
                # ---------------------------------------------------------
                if intensity_map.max() > 0:
                    # 1. Suavização Gaussiana (efeito arredondado e fluido estilo radar)
                    blur_ksize = max(31, int(min(h, w) / 10) | 1)  # Garante número ímpar
                    intensity_map = cv2.GaussianBlur(intensity_map, (blur_ksize, blur_ksize), 0)

                    # 2. Normalização (0 a 255)
                    intensity_map = (intensity_map / intensity_map.max() * 255).astype(np.uint8)

                    # 3. Mapeamento de Cores JET (Azul/Verde -> Amarelo -> Laranja -> Vermelho)
                    heatmap_color = cv2.applyColorMap(intensity_map, cv2.COLORMAP_JET)

                    # 4. Criação da Máscara de Transparência
                    # Remove cores nas áreas sem infecção, deixando a imagem original visível
                    _, mask = cv2.threshold(intensity_map, 25, 255, cv2.THRESH_BINARY)

                    # 5. Aplicação da mistura com opacidade parcial (efeito marca-texto)
                    alpha = 0.55
                    overlay = cv2.addWeighted(img_np, 1 - alpha, heatmap_color, alpha, 0)

                    # Aplica o overlay de calor apenas nas regiões afetadas
                    resultado_final = img_np.copy()
                    resultado_final[mask > 0] = overlay[mask > 0]
                else:
                    resultado_final = img_np.copy()

                # ---------------------------------------------------------
                # EXIBIÇÃO DOS RESULTADOS
                # ---------------------------------------------------------
                st.subheader("2. Resultado do Mapeamento Térmico de Severidade")

                col_res1, col_res2 = st.columns([2, 1])
                with col_res1:
                    st.image(resultado_final, caption="Mapa Térmico de Anomalias (Transparência Orgânica)",
                             use_container_width=True)

                with col_res2:
                    st.metric(label="📊 Taxa de Infestação do Talhão", value=f"{taxa_infestacao:.1f}%")
                    st.write(f"- **Zonas Escaneadas:** {total_quadros}")
                    st.write(f"- **Zonas Afetadas:** {quadros_infectados}")

                    if taxa_infestacao < 10:
                        st.success(
                            "✅ **Nível de Severidade: BAIXO**\nSem áreas críticas visíveis. Talhão em boas condições.")
                    elif taxa_infestacao < 30:
                        st.warning(
                            "⚠️ **Nível de Severidade: MÉDIO**\nFocos localizados identificados. Aplicação pontual recomendada.")
                    else:
                        st.error(
                            "🚨 **Nível de Severidade: CRÍTICO**\nManchas de alta infestação. Planejar intervenção em área total.")