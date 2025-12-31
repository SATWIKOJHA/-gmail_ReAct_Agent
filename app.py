"""
Gmail Streamlit App
A web application to view and send emails using Gmail.
Supports both App Password and Google OAuth 2.0 authentication.
"""

import streamlit as st
from urllib.parse import urlencode, parse_qs
from gmail_service import authenticate, fetch_emails, send_email

# Try to import OAuth service (may fail if dependencies not installed)
try:
    from oauth_service import (
        get_authorization_url, 
        exchange_code_for_credentials,
        fetch_emails_oauth,
        send_email_oauth,
        get_user_email,
        credentials_to_dict,
        credentials_from_dict
    )
    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False


# Page configuration
st.set_page_config(
    page_title="Gmail Client",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS for better styling
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding: 2rem 3rem;
    }
    
    /* Email header in detail view */
    .email-header {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #e8eaed;
    }
    
    .email-header-row {
        display: flex;
        align-items: flex-start;
        gap: 1rem;
    }
    
    .email-avatar {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: linear-gradient(135deg, #EA4335 0%, #FBBC05 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 600;
        font-size: 1.2rem;
        flex-shrink: 0;
    }
    
    .email-meta {
        flex-grow: 1;
    }
    
    .email-sender {
        font-size: 1rem;
        font-weight: 600;
        color: #202124;
        margin-bottom: 0.2rem;
    }
    
    .email-recipient {
        font-size: 0.85rem;
        color: #5f6368;
    }
    
    .email-timestamp {
        font-size: 0.8rem;
        color: #80868b;
        text-align: right;
    }
    
    .email-subject-line {
        font-size: 1.3rem;
        font-weight: 500;
        color: #202124;
        margin: 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #e8eaed;
    }
    
    /* Email body styling */
    .email-body {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e8eaed;
        font-size: 0.95rem;
        line-height: 1.7;
        color: #202124;
        white-space: pre-wrap;
        word-wrap: break-word;
        font-family: 'Google Sans', Roboto, Arial, sans-serif;
    }
    
    /* Action buttons */
    .email-actions {
        display: flex;
        gap: 0.5rem;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #e8eaed;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-size: 0.95rem !important;
        background: #f8f9fa !important;
        border-radius: 8px !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: #e8eaed !important;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 24px;
        padding: 0.5rem 2rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(234, 67, 53, 0.3);
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Google AI Studio style Snow Animation */
    @keyframes snowfall {
        0% {
            transform: translateY(-10vh) translateX(0) rotate(0deg);
            opacity: 1;
        }
        100% {
            transform: translateY(100vh) translateX(100px) rotate(360deg);
            opacity: 0.3;
        }
    }
    
    @keyframes snowfall-reverse {
        0% {
            transform: translateY(-10vh) translateX(0) rotate(0deg);
            opacity: 1;
        }
        100% {
            transform: translateY(100vh) translateX(-100px) rotate(-360deg);
            opacity: 0.3;
        }
    }
    
    .snowflake {
        position: fixed;
        top: -10vh;
        z-index: 9999;
        color: #fff;
        font-size: 1.5rem;
        text-shadow: 0 0 5px rgba(255,255,255,0.8), 0 0 10px rgba(173,216,230,0.6);
        pointer-events: none;
        animation-timing-function: linear;
        animation-iteration-count: 1;
        animation-fill-mode: forwards;
    }
    
    .snow-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        pointer-events: none;
        z-index: 9999;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


def get_oauth_credentials():
    """Get OAuth credentials from Streamlit secrets."""
    try:
        client_id = st.secrets.get("google_oauth", {}).get("client_id", "")
        client_secret = st.secrets.get("google_oauth", {}).get("client_secret", "")
        
        if client_id and client_secret and "YOUR_CLIENT_ID" not in client_id:
            return client_id, client_secret
        return None, None
    except Exception:
        return None, None


def init_session_state():
    """Initialize session state variables."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "email" not in st.session_state:
        st.session_state.email = ""
    if "password" not in st.session_state:
        st.session_state.password = ""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "inbox"
    if "auth_method" not in st.session_state:
        st.session_state.auth_method = None  # 'app_password' or 'oauth'
    if "oauth_credentials" not in st.session_state:
        st.session_state.oauth_credentials = None
    if "email_page" not in st.session_state:
        st.session_state.email_page = 1  # Current page for pagination
    if "emails_per_page" not in st.session_state:
        st.session_state.emails_per_page = 25  # Emails per page


def handle_oauth_callback():
    """Handle OAuth callback with authorization code."""
    query_params = st.query_params
    
    if "code" in query_params:
        code = query_params["code"]
        client_id, client_secret = get_oauth_credentials()
        
        if client_id and client_secret:
            # Get the current URL for redirect
            redirect_uri = "http://localhost:8501"
            
            success, result = exchange_code_for_credentials(
                code, client_id, client_secret, redirect_uri
            )
            
            if success:
                credentials = result
                st.session_state.logged_in = True
                st.session_state.auth_method = 'oauth'
                st.session_state.oauth_credentials = credentials_to_dict(credentials)
                st.session_state.email = get_user_email(credentials)
                st.session_state.just_logged_in = True  # Flag for welcome animation
                
                # Clear the code from URL
                st.query_params.clear()
                st.rerun()
            else:
                st.error(f"OAuth Error: {result}")
                st.query_params.clear()


def login_page():
    """Render the login page with tabs for login and setup guides."""
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: #EA4335; font-size: 3rem; margin-bottom: 0.5rem;">📧 Gmail Client</h1>
        <p style="color: #5f6368; font-size: 1.1rem;">Sign in to access your emails</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check for OAuth callback
    if OAUTH_AVAILABLE:
        handle_oauth_callback()
    
    # Create tabs for Login, App Password Setup, and OAuth Setup
    if OAUTH_AVAILABLE:
        tab1, tab2, tab3 = st.tabs(["🔐 Login", "🔑 App Password Setup", "🔗 Google OAuth Setup"])
    else:
        tab1, tab2 = st.tabs(["🔐 Login", "🔑 App Password Setup"])
        tab3 = None
    
    with tab1:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # OAuth Login Section
            client_id, client_secret = get_oauth_credentials()
            oauth_configured = client_id is not None and OAUTH_AVAILABLE
            
            if oauth_configured:
                st.markdown("### 🔗 Quick Login with Google")
                st.markdown("One-click sign in using your Google account")
                
                redirect_uri = "http://localhost:8501"
                auth_url, state = get_authorization_url(client_id, client_secret, redirect_uri)
                
                st.link_button(
                    "🔵 Sign in with Google",
                    auth_url,
                    use_container_width=True,
                    type="primary"
                )
                
                st.markdown("---")
                st.markdown("**Or use App Password:**")
            else:
                st.markdown("### Sign In")
            
            st.markdown("Use your Gmail address and **App Password**")
            
            email_input = st.text_input(
                "Gmail Address",
                placeholder="your.email@gmail.com",
                key="email_input"
            )
            
            password_input = st.text_input(
                "App Password",
                type="password",
                placeholder="Your 16-character app password",
                key="password_input"
            )
            
            st.markdown("")
            
            if st.button("🚀 Sign In with App Password", use_container_width=True):
                if not email_input or not password_input:
                    st.error("⚠️ Please enter both email and app password.")
                else:
                    with st.spinner("Authenticating..."):
                        success, message = authenticate(email_input, password_input)
                        
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.email = email_input
                            st.session_state.password = password_input
                            st.session_state.auth_method = 'app_password'
                            st.session_state.just_logged_in = True  # Flag for animation
                            st.success("✅ " + message)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ " + message)
            
            st.markdown("")
            
            if not oauth_configured:
                st.info("💡 Want **one-click Google login**? Check the **'Google OAuth Setup'** tab!")
            
            # New User Section - Inline App Password Setup
            st.markdown("---")
            
            with st.expander("🆕 **New User? Create App Password Here**", expanded=False):
                st.markdown("""
                <div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); 
                     padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                    <h4 style="color: #2e7d32; margin: 0;">Quick Setup Guide</h4>
                    <p style="color: #388e3c; margin: 0.5rem 0 0 0;">Follow these 3 steps to create your App Password</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Step 1
                st.markdown("### Step 1️⃣ Enable 2-Step Verification")
                st.markdown("You need 2-Step Verification enabled on your Google account first.")
                st.link_button(
                    "🔗 Open Google Security Settings",
                    "https://myaccount.google.com/security",
                    use_container_width=True
                )
                st.markdown("")
                
                # Step 2
                st.markdown("### Step 2️⃣ Go to App Passwords Page")
                st.markdown("Once 2-Step Verification is enabled, create an App Password.")
                st.link_button(
                    "🔗 Open App Passwords Page",
                    "https://myaccount.google.com/apppasswords",
                    use_container_width=True,
                    type="primary"
                )
                st.markdown("")
                
                # Step 3
                st.markdown("### Step 3️⃣ Generate Password")
                st.markdown("""
                1. Select **Mail** as the app
                2. Select **Windows Computer** as the device
                3. Click **Generate**
                4. **Copy the 16-character password**
                """)
                
                st.success("✅ **Done!** Paste the 16-character password in the App Password field above and sign in!")
    
    with tab2:
        render_app_password_guide()
    
    if tab3 is not None:
        with tab3:
            render_oauth_setup_guide()


def render_app_password_guide():
    """Render the App Password setup guide."""
    st.markdown("""
    ## 🔑 How to Create a Google App Password
    
    An **App Password** is a 16-character code that gives this app permission to access your Gmail.
    
    ---
    
    ### Step 1: Enable 2-Step Verification
    """)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("""
        1. Click the button to open Google Security settings
        2. Find **"2-Step Verification"** under "How you sign in to Google"
        3. Click it and follow the prompts to enable it
        """)
    with col2:
        st.link_button("🔗 Open Security", "https://myaccount.google.com/security", use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("### Step 2: Generate App Password")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("""
        1. Click the button to open App Passwords page
        2. Select **Mail** and **Windows Computer**
        3. Click **Generate**
        """)
    with col2:
        st.link_button("🔗 App Passwords", "https://myaccount.google.com/apppasswords", use_container_width=True)
    
    st.markdown("---")
    
    st.success("""
    📋 **Copy the 16-character password** shown by Google and use it in the Login tab!
    """)


def render_oauth_setup_guide():
    """Render the Google OAuth setup guide."""
    # Check current status
    client_id, client_secret = get_oauth_credentials()
    
    if client_id:
        st.success("✅ **OAuth is configured!** You can use 'Sign in with Google' on the Login tab.")
        st.markdown("---")
    
    st.markdown("""
    ## 🔗 Set Up Google OAuth 2.0
    
    OAuth allows users to log in with one click using their Google account. 
    This requires a one-time setup in Google Cloud Console.
    
    ---
    
    ### Step 1: Create a Google Cloud Project
    """)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("""
        1. Click the button to open Google Cloud Console
        2. Click **"Select a project"** → **"New Project"**
        3. Name it (e.g., "Gmail Client App")
        4. Click **Create**
        """)
    with col2:
        st.link_button("🔗 Cloud Console", "https://console.cloud.google.com/", use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("### Step 2: Enable Gmail API")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("""
        1. In your project, go to **APIs & Services** → **Library**
        2. Search for **"Gmail API"**
        3. Click on it and click **Enable**
        """)
    with col2:
        st.link_button("🔗 API Library", "https://console.cloud.google.com/apis/library", use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("### Step 3: Configure OAuth Consent Screen")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("""
        1. Go to **APIs & Services** → **OAuth consent screen**
        2. Select **External** and click **Create**
        3. Fill in App name, User support email, Developer email
        4. Click **Save and Continue** through the steps
        5. Add your email as a **Test User**
        """)
    with col2:
        st.link_button("🔗 Consent Screen", "https://console.cloud.google.com/apis/credentials/consent", use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("### Step 4: Create OAuth Credentials")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("""
        1. Go to **APIs & Services** → **Credentials**
        2. Click **Create Credentials** → **OAuth client ID**
        3. Select **Web application**
        4. Add Authorized redirect URI: `http://localhost:8501`
        5. Click **Create** and copy the **Client ID** and **Client Secret**
        """)
    with col2:
        st.link_button("🔗 Credentials", "https://console.cloud.google.com/apis/credentials", use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("### Step 5: Add Credentials to App")
    
    st.code("""
# Edit the file: .streamlit/secrets.toml

[google_oauth]
client_id = "your-client-id.apps.googleusercontent.com"
client_secret = "your-client-secret"
    """, language="toml")
    
    st.info("📂 The file is located at: `.streamlit/secrets.toml`")
    
    st.markdown("---")
    
    st.warning("""
    ⚠️ **After adding credentials:**
    1. Restart the Streamlit app
    2. The "Sign in with Google" button will appear on the Login tab
    """)


def sidebar():
    """Render the sidebar with navigation."""
    with st.sidebar:
        auth_icon = "🔗" if st.session_state.auth_method == 'oauth' else "🔑"
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: #EA4335; margin-bottom: 0;">📧 Gmail</h2>
            <p style="color: #5f6368; font-size: 0.9rem;">{st.session_state.email}</p>
            <p style="color: #80868b; font-size: 0.75rem;">{auth_icon} {'OAuth' if st.session_state.auth_method == 'oauth' else 'App Password'}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Navigation buttons
        if st.button("📥 Inbox", use_container_width=True, 
                     type="primary" if st.session_state.current_page == "inbox" else "secondary"):
            st.session_state.current_page = "inbox"
            st.rerun()
        
        if st.button("✏️ Compose", use_container_width=True,
                     type="primary" if st.session_state.current_page == "compose" else "secondary"):
            st.session_state.current_page = "compose"
            st.rerun()
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.email = ""
            st.session_state.password = ""
            st.session_state.auth_method = None
            st.session_state.oauth_credentials = None
            st.session_state.current_page = "inbox"
            st.rerun()


def inbox_page():
    """Render the inbox page."""
    
    # Welcome animation for first load after login
    if st.session_state.get("just_logged_in", False):
        st.balloons()
        st.toast(f"🎉 Welcome, {st.session_state.email.split('@')[0]}!", icon="👋")
        st.session_state.just_logged_in = False
    
    st.markdown("""
    <h1 style="color: #202124; margin-bottom: 1.5rem;">
        📥 Inbox
    </h1>
    """, unsafe_allow_html=True)
    
    # Controls row: Emails per page, Page info, Refresh
    col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
    
    with col1:
        emails_per_page = st.selectbox(
            "Emails per page",
            options=[10, 25, 50, 100],
            index=[10, 25, 50, 100].index(st.session_state.emails_per_page),
            key="per_page_select",
            label_visibility="collapsed"
        )
        if emails_per_page != st.session_state.emails_per_page:
            st.session_state.emails_per_page = emails_per_page
            st.session_state.email_page = 1
            st.rerun()
    
    with col4:
        refresh = st.button("🔄 Refresh")
    
    # Show snowfall animation on refresh (Streamlit built-in)
    if refresh:
        st.session_state.email_page = 1  # Reset to first page on refresh
        st.snow()
        st.toast("❄️ Refreshing your inbox...", icon="🔄")
    
    # Fetch more emails for pagination (fetch 100 to allow pagination)
    with st.spinner("Loading emails..."):
        total_to_fetch = 100  # Fetch more emails for pagination
        if st.session_state.auth_method == 'oauth' and st.session_state.oauth_credentials:
            credentials = credentials_from_dict(st.session_state.oauth_credentials)
            success, result = fetch_emails_oauth(credentials, count=total_to_fetch)
        else:
            success, result = fetch_emails(
                st.session_state.email,
                st.session_state.password,
                count=total_to_fetch
            )
    
    if success:
        all_emails = result
        if not all_emails:
            st.info("📭 Your inbox is empty!")
        else:
            # Pagination calculations
            total_emails = len(all_emails)
            per_page = st.session_state.emails_per_page
            total_pages = (total_emails + per_page - 1) // per_page
            current_page = st.session_state.email_page
            
            # Ensure current page is valid
            if current_page > total_pages:
                current_page = total_pages
                st.session_state.email_page = current_page
            
            # Get emails for current page
            start_idx = (current_page - 1) * per_page
            end_idx = min(start_idx + per_page, total_emails)
            emails = all_emails[start_idx:end_idx]
            
            # Pagination controls at top
            pcol1, pcol2, pcol3, pcol4, pcol5 = st.columns([1, 1, 3, 1, 1])
            
            with pcol1:
                if st.button("⏮️ First", disabled=current_page == 1):
                    st.session_state.email_page = 1
                    st.rerun()
            
            with pcol2:
                if st.button("◀️ Prev", disabled=current_page == 1):
                    st.session_state.email_page = current_page - 1
                    st.rerun()
            
            with pcol3:
                st.markdown(f"""
                <div style="text-align: center; padding: 0.5rem;">
                    <strong>Page {current_page} of {total_pages}</strong>
                    <br><span style="color: #5f6368; font-size: 0.85rem;">
                    Showing {start_idx + 1}-{end_idx} of {total_emails} emails</span>
                </div>
                """, unsafe_allow_html=True)
            
            with pcol4:
                if st.button("Next ▶️", disabled=current_page == total_pages):
                    st.session_state.email_page = current_page + 1
                    st.rerun()
            
            with pcol5:
                if st.button("Last ⏭️", disabled=current_page == total_pages):
                    st.session_state.email_page = total_pages
                    st.rerun()
            
            st.markdown("---")
            
            for idx, email_item in enumerate(emails):
                # Get sender initial for avatar
                sender_name = email_item['from'].split('<')[0].strip() if '<' in email_item['from'] else email_item['from'].split('@')[0]
                sender_initial = sender_name[0].upper() if sender_name else '?'
                
                # Create an expander for each email
                with st.expander(
                    f"📧 **{email_item['subject'][:50]}{'...' if len(email_item['subject']) > 50 else ''}**",
                    expanded=False
                ):
                    # Gmail-like email header with avatar
                    st.markdown(f"""
                    <div class="email-header">
                        <div class="email-header-row">
                            <div class="email-avatar">{sender_initial}</div>
                            <div class="email-meta">
                                <div class="email-sender">{sender_name}</div>
                                <div class="email-recipient">to me</div>
                            </div>
                            <div class="email-timestamp">{email_item['date']}</div>
                        </div>
                        <div class="email-subject-line">{email_item['subject']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Full email body with Gmail-like styling
                    st.markdown(f"""
                    <div class="email-body">
{email_item['body']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("")
                    
                    # Action buttons
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
                    with col1:
                        if st.button("↩️ Reply", key=f"reply_{idx}"):
                            st.session_state.current_page = "compose"
                            st.session_state.reply_to = email_item['from']
                            st.session_state.reply_subject = f"Re: {email_item['subject']}"
                            st.rerun()
                    with col2:
                        if st.button("↪️ Forward", key=f"forward_{idx}"):
                            st.session_state.current_page = "compose"
                            st.session_state.reply_subject = f"Fwd: {email_item['subject']}"
                            st.rerun()
    else:
        st.error(f"❌ {result}")


def compose_page():
    """Render the compose email page."""
    st.markdown("""
    <h1 style="color: #202124; margin-bottom: 1.5rem;">
        ✏️ Compose Email
    </h1>
    """, unsafe_allow_html=True)
    
    # Get reply info if available
    default_to = st.session_state.get("reply_to", "")
    default_subject = st.session_state.get("reply_subject", "")
    
    # Clear reply info after using it
    if "reply_to" in st.session_state:
        del st.session_state.reply_to
    if "reply_subject" in st.session_state:
        del st.session_state.reply_subject
    
    with st.form("compose_form", clear_on_submit=True):
        to_email = st.text_input(
            "To",
            value=default_to,
            placeholder="recipient@example.com"
        )
        
        subject = st.text_input(
            "Subject",
            value=default_subject,
            placeholder="Enter email subject"
        )
        
        body = st.text_area(
            "Message",
            placeholder="Write your message here...",
            height=250
        )
        
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            submitted = st.form_submit_button("📤 Send", type="primary")
        
        with col2:
            clear = st.form_submit_button("🗑️ Clear")
    
    if submitted:
        if not to_email:
            st.error("⚠️ Please enter a recipient email address.")
        elif not subject:
            st.error("⚠️ Please enter a subject.")
        elif not body:
            st.error("⚠️ Please enter a message.")
        else:
            with st.spinner("Sending email..."):
                if st.session_state.auth_method == 'oauth' and st.session_state.oauth_credentials:
                    credentials = credentials_from_dict(st.session_state.oauth_credentials)
                    success, message = send_email_oauth(
                        credentials,
                        to_email,
                        subject,
                        body,
                        st.session_state.email
                    )
                else:
                    success, message = send_email(
                        st.session_state.email,
                        st.session_state.password,
                        to_email,
                        subject,
                        body
                    )
                
                if success:
                    st.success(f"✅ {message}")
                    st.balloons()
                else:
                    st.error(f"❌ {message}")


def main():
    """Main application entry point."""
    init_session_state()
    
    if not st.session_state.logged_in:
        login_page()
    else:
        sidebar()
        
        if st.session_state.current_page == "inbox":
            inbox_page()
        elif st.session_state.current_page == "compose":
            compose_page()


if __name__ == "__main__":
    main()
