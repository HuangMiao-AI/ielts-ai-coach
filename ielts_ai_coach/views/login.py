"""Simplified Chinese login and registration views."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.auth import (
    AccountNotFoundError,
    IncorrectPasswordError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidPasswordError,
    InvalidUsernameError,
    UsernameAlreadyExistsError,
    login_user,
    register_user,
)


def _render_login_form() -> None:
    """Render the login form and process one login attempt."""

    with st.form("login_form"):
        username = st.text_input(
            "用户名",
            key="login_username",
            placeholder="请输入用户名",
            autocomplete="username",
        )
        password = st.text_input(
            "密码",
            key="login_password",
            type="password",
            placeholder="请输入密码",
            autocomplete="current-password",
        )
        submitted = st.form_submit_button(
            "登录",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    try:
        login_user(username, password)
    except AccountNotFoundError:
        st.error("未找到该账号，请检查用户名或先注册。")
    except IncorrectPasswordError:
        st.error("密码不正确，请重新输入。")
    except InvalidCredentialsError:
        st.error("用户名或密码不正确。")
    except InactiveUserError:
        st.error("该账号当前不可用。")
    else:
        st.rerun()


def _render_registration_form() -> None:
    """Render the registration form and create one account."""

    with st.form("registration_form"):
        username = st.text_input(
            "设置用户名",
            key="register_username",
            placeholder="3–24位英文字母、数字或下划线",
            autocomplete="username",
        )
        password = st.text_input(
            "设置密码",
            key="register_password",
            type="password",
            placeholder="至少10个字符",
            autocomplete="new-password",
        )
        password_confirmation = st.text_input(
            "确认密码",
            key="register_password_confirmation",
            type="password",
            placeholder="请再次输入密码",
            autocomplete="new-password",
        )
        submitted = st.form_submit_button(
            "创建账号",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return
    if password != password_confirmation:
        st.error("两次输入的密码不一致。")
        return

    try:
        register_user(username, password)
    except InvalidUsernameError:
        st.error("用户名必须为3–24位英文字母、数字或下划线。")
    except InvalidPasswordError:
        st.error("密码长度必须为10–128个字符。")
    except UsernameAlreadyExistsError:
        st.error("该用户名已被使用，请更换一个。")
    else:
        st.rerun()


def render_auth_page() -> None:
    """Render the public authentication page."""

    st.markdown(
        """
        <section class="auth-hero">
            <div class="auth-kicker">IELTS AI COACH</div>
            <h1>让每一次学习更有方向</h1>
            <p>创建你的个人账号，安全保存学习进度。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="auth_form_shell"):
        login_tab, registration_tab = st.tabs(["登录", "注册"])
        with login_tab:
            _render_login_form()
        with registration_tab:
            _render_registration_form()

    st.caption("当前版本仅包含账号与数据基础功能。")
