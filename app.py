import streamlit as st
import requests
from user_agents import parse
import uuid
import json
import os
from streamlit.runtime.scriptrunner import get_script_run_ctx
import streamlit.components.v1 as components

# Configuração inicial
st.set_page_config(page_title="CyberTrack", page_icon="🕵️")

# Funções auxiliares
def get_client_info():
    try:
        # Obter IP público usando serviço externo
        ip = requests.get('https://api.ipify.org').text
    except:
        ip = "IP não detectado"
    
    # Obter User-Agent via JavaScript
    user_agent = st.query_params.get('ua', [''])[0]
    
    return {'ip': ip, 'user_agent': user_agent}

def inject_user_agent():
    # JavaScript para capturar User-Agent e enviar via URL
    js_code = """
    <script>
    function getUA() {
        var ua = navigator.userAgent;
        window.location.href = window.location.href + "&ua=" + encodeURIComponent(ua);
    }
    getUA();
    </script>
    """
    components.html(js_code, height=0)

def parse_user_agent(user_agent):
    if not user_agent:
        return {}
    try:
        ua = parse(user_agent)
        return {
            'Sistema Operacional': f"{ua.os.family} {ua.os.version_string}",
            'Navegador': f"{ua.browser.family} {ua.browser.version_string}",
            'Dispositivo': f"{ua.device.family}",
            'User Agent': user_agent
        }
    except:
        return {}

def load_data():
    if os.path.exists('data.json'):
        with open('data.json') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open('data.json', 'w') as f:
        json.dump(data, f)

# Página principal
def main():
    query_params = st.query_params
    tracking_id = query_params.get("tracking_id", [None])[0]

    if tracking_id:
        # Modo de captura (acesso pelo criminoso)
        if 'ua' not in query_params:
            inject_user_agent()
            st.stop()

        data = load_data()
        entry = data.get(tracking_id, {})
        
        if not entry.get('captured'):
            client_info = get_client_info()
            entry['ip'] = client_info['ip']
            entry.update(parse_user_agent(client_info['user_agent']))
            entry['captured'] = True
            data[tracking_id] = entry
            save_data(data)

        # Restante do código de download...
        st.title("📥 Download do Arquivo")
        if entry.get('file_path') and os.path.exists(entry['file_path']):
            with open(entry['file_path'], "rb") as f:
                st.download_button(
                    label="Baixar Arquivo",
                    data=f,
                    file_name=entry.get('file_name', 'arquivo.exe'),
                    help="Clique para baixar o arquivo solicitado"
                )
        else:
            st.warning("Arquivo não disponível")
        
        st.markdown("---")
        st.info("⚠️ Este arquivo pode conter conteúdo malicioso. Não execute arquivos de fontes desconhecidas.")

    else:
        # Modo de gestão (acesso pela vítima)
        st.title("🔍 CyberTrack - Rastreamento Cibernético")
        st.markdown("""
        ### Como usar:
        1. Gere um link único
        2. Envie o link para o criminoso
        3. Quando ele acessar, suas informações serão capturadas
        """)

        # Geração de novo link
        if st.button("🆔 Gerar Novo Link de Rastreamento"):
            new_id = str(uuid.uuid4())
            data = load_data()
            data[new_id] = {'captured': False}
            save_data(data)
            st.session_state.generated_id = new_id
            st.success("Link gerado com sucesso!")
            
            link = f"http://localhost:8501/?tracking_id={new_id}"
            st.markdown(f"""
            **Envie este link para o criminoso:**
            ```{link}```
            """)

        # Upload de arquivo isca
        if 'generated_id' in st.session_state:
            uploaded_file = st.file_uploader("📤 Carregue o arquivo isca", type=None)
            if uploaded_file:
                data = load_data()
                entry = data[st.session_state.generated_id]
                
                # Salvar arquivo
                file_path = f"uploads/{st.session_state.generated_id}_{uploaded_file.name}"
                os.makedirs("uploads", exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                entry['file_name'] = uploaded_file.name
                entry['file_path'] = file_path
                save_data(data)
                st.success("Arquivo configurado!")

        # Verificação de resultados
        st.markdown("---")
        track_id = st.text_input("🔎 Insira o ID de rastreamento para verificar resultados:")
        if track_id:
            data = load_data()
            entry = data.get(track_id, {})
            
            if entry:
                st.subheader("Informações Capturadas:")
                if entry.get('captured'):
                    cols = st.columns(2)
                    cols[0].metric("IP", entry.get('ip', 'Desconhecido'))
                    cols[1].metric("Sistema Operacional", entry.get('Sistema Operacional', 'Desconhecido'))
                    
                    st.json({
                        "Dispositivo": entry.get('Dispositivo'),
                        "Navegador": entry.get('Navegador'),
                        "User Agent": entry.get('User Agent')
                    })
                else:
                    st.warning("O criminoso ainda não acessou o link")
            else:
                st.error("ID de rastreamento inválido")

        # Avisos legais
        st.markdown("---")
        st.caption("""
        ⚠️ **Aviso Legal:**  
        Este sistema é apenas para fins educacionais e de demonstração técnica.  
        O uso indevido desta ferramenta é estritamente proibido.
        """)

if __name__ == "__main__":
    main()
