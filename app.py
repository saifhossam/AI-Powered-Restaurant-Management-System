"""
Restaurant Manager — Streamlit App
===================================
Install deps before running:
    pip install streamlit requests pandas streamlit-autorefresh
"""

import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh   # pip install streamlit-autorefresh

# ─────────────────────────────────────────────
#  ⚙️  CONFIGURATION
# ─────────────────────────────────────────────
BASEROW_URL       = "https://api.baserow.io"
API_TOKEN         = "LdvxIZnd1FaqL7G7vMGS1MDp6j1W4UxG"
TABLE_USERS       = 927620
TABLE_ORDERS      = 927618
TABLE_ORDER_ITEMS = 927619

HEADERS = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type":  "application/json",
}

REFRESH_INTERVAL_MS = 30_000   # 30 seconds


# ─────────────────────────────────────────────
#  PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Restaurant Manager",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    body { font-family: 'Segoe UI', sans-serif; }
    section[data-testid="stSidebar"] { background: #1a1a2e; }
    section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    .badge {
        display:inline-block; padding:4px 14px; border-radius:20px;
        font-size:0.75rem; font-weight:700; letter-spacing:0.05em; text-transform:uppercase;
    }
    .badge-cashier  { background:#fef3c7; color:#92400e; }
    .badge-chef     { background:#d1fae5; color:#065f46; }
    .badge-delivery { background:#dbeafe; color:#1e40af; }
    .status-pill {
        display:inline-block; padding:2px 10px; border-radius:12px;
        font-size:0.78rem; font-weight:600;
    }
    .s-pending   { background:#fef9c3; color:#713f12; }
    .s-cooking   { background:#ffedd5; color:#9a3412; }
    .s-out       { background:#ede9fe; color:#4c1d95; }
    .s-delivered { background:#dcfce7; color:#166534; }
    .order-card  {
        background:#f8fafc; border:1px solid #e2e8f0;
        border-radius:12px; padding:20px; margin-bottom:16px;
    }
    div[data-testid="stDataFrame"]       { border-radius:10px; overflow:hidden; }
    div[data-testid="stButton"] > button { border-radius:8px; font-weight:600; transition:all .2s; }
    /* Dismiss button styling */
    div[data-testid="stButton"] > button[kind="secondary"].dismiss-btn {
        background: transparent; border: none; color: #78350f;
        font-size: 1.1rem; padding: 4px 8px; line-height: 1;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  API HELPERS
# ─────────────────────────────────────────────
def get_rows(table_id: int, filters: str = "") -> list[dict]:
    rows, page = [], 1
    while True:
        url = (f"{BASEROW_URL}/api/database/rows/table/{table_id}/"
               f"?user_field_names=true&page={page}&size=100{filters}")
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            st.error(f"Baserow error {r.status_code}: {r.text}")
            return []
        data = r.json()
        rows.extend(data.get("results", []))
        if not data.get("next"):
            break
        page += 1
    return rows


def update_row(table_id: int, row_id: int, payload: dict) -> tuple[bool, str]:
    url = f"{BASEROW_URL}/api/database/rows/table/{table_id}/{row_id}/?user_field_names=true"
    r   = requests.patch(url, json=payload, headers=HEADERS)
    return (True, "") if r.status_code == 200 else (False, f"HTTP {r.status_code}: {r.text}")


def to_str(val) -> str:
    if val is None or val is False:
        return ""
    if isinstance(val, dict):
        return str(val.get("value", ""))
    return str(val)


def clean_df(df: pd.DataFrame, drop_cols: list = None) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].apply(lambda v:
            v.get("value", "") if isinstance(v, dict)
            else (", ".join(
                str(x.get("value", x)) if isinstance(x, dict) else str(x)
                for x in v
            ) if isinstance(v, list) else v)
        )
    if drop_cols:
        drop_lower   = [c.lower() for c in drop_cols]
        cols_to_drop = [c for c in df.columns if c.lower() in drop_lower]
        df = df.drop(columns=cols_to_drop, errors="ignore")
    return df


def authenticate(name: str, password: str):
    users = get_rows(TABLE_USERS)
    for user in users:
        db_name = to_str(user.get("name")).strip().lower()
        db_pass = to_str(user.get("password")).strip()
        if db_name == name.strip().lower() and db_pass == password.strip():
            return user
    return None


def resolve_link_field(val) -> str:
    if isinstance(val, list):
        return ", ".join(
            item.get("value", str(item)) if isinstance(item, dict) else str(item)
            for item in val
        )
    if isinstance(val, dict):
        return val.get("value", str(val))
    return str(val) if val is not None else ""


def item_order_id(item: dict) -> int | None:
    val = item.get("Orders") or item.get("order") or item.get("order_id")
    if isinstance(val, list) and val:
        return val[0].get("id")
    if isinstance(val, dict):
        return val.get("id")
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────
#  SESSION PERSISTENCE  (survives browser F5)
# ─────────────────────────────────────────────
def save_session_to_params(user: dict):
    """Store the user row-ID in the URL query string."""
    st.query_params["uid"] = str(user["id"])


def restore_session_from_params() -> bool:
    uid_str = st.query_params.get("uid", "")
    if not uid_str:
        return False
    try:
        uid = int(uid_str)
    except ValueError:
        return False
    users = get_rows(TABLE_USERS)
    for u in users:
        if u.get("id") == uid:
            st.session_state.user = u
            return True
    st.query_params.clear()
    return False


def clear_session():
    st.session_state.user            = None
    st.session_state.seen_orders     = {}
    st.session_state.seen_order_ids  = set()
    st.session_state.seen_item_ids   = set()
    st.query_params.clear()


# ─────────────────────────────────────────────
#  SESSION STATE INIT
# ─────────────────────────────────────────────
_defaults = {
    "user":              None,
    "seen_orders":       {},       # {order_id: status_lower}
    "seen_order_ids":    set(),    # set of int
    "seen_item_ids":     set(),    # set of int
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# Try to restore session from URL if browser was refreshed
if st.session_state.user is None:
    restore_session_from_params()


# ─────────────────────────────────────────────
#  NOTIFICATION HELPERS
# ─────────────────────────────────────────────
NOTIFY_RULES = {
    "chef":        ["cooking"],
    "deliveryman": ["out for delivery"],
    "cashier":     ["cooked", "delivered"],
}

_NOTIFY_MSG = {
    "cooking":          ("🔥", "New order in the kitchen!"),
    "out for delivery": ("🛵", "New order ready for delivery!"),
    "cooked":           ("✅", "An order is cooked and ready!"),
    "delivered":        ("📦", "An order has been delivered!"),
}


def check_notifications(role: str, all_orders: list, all_items: list | None = None):
    role_key          = role.lower().replace(" ", "")
    relevant_statuses = NOTIFY_RULES.get(role_key, [])

    # ── 1. Status-change toasts ──────────────────────────────────
    current_snapshot = {
        o["id"]: to_str(o.get("status")).strip().lower()
        for o in all_orders
    }
    prev_snapshot = st.session_state.seen_orders

    if prev_snapshot:
        for order in all_orders:
            oid    = order["id"]
            status = to_str(order.get("status")).strip().lower()
            label  = to_str(order.get("order_id")) or f"#{oid}"
            prev   = prev_snapshot.get(oid, "pending")

            if status != prev and status in relevant_statuses:
                icon, msg = _NOTIFY_MSG.get(status, ("🔔", "Order update!"))
                st.toast(f"{icon} Order **{label}** — {msg}", icon="🔔")
                # Reset dismissed so the banner shows again for the new event
                st.session_state.dismissed_banner = False

    st.session_state.seen_orders = current_snapshot

    # ── 2. New orders in Orders table (Cashier) ──────────────────
    if role_key == "cashier":
        current_order_ids = {o["id"] for o in all_orders}
        prev_order_ids    = st.session_state.seen_order_ids

        if prev_order_ids:
            for oid in (current_order_ids - prev_order_ids):
                o     = next((x for x in all_orders if x["id"] == oid), {})
                label = to_str(o.get("order_id")) or f"#{oid}"
                st.toast(f"🛎️ New order added — **{label}**", icon="🆕")

        st.session_state.seen_order_ids = current_order_ids

    # ── 3. New rows in Order Items table (Cashier) ───────────────
    if role_key == "cashier" and all_items is not None:
        current_item_ids = {i["id"] for i in all_items}
        prev_item_ids    = st.session_state.seen_item_ids

        if prev_item_ids:
            new_count = len(current_item_ids - prev_item_ids)
            if new_count:
                st.toast(f"🛎️ {new_count} new item(s) added to orders!", icon="🆕")

        st.session_state.seen_item_ids = current_item_ids


def render_notification_banner(role: str, all_orders: list):
    """Persistent amber banner with pending-action count."""
    role_key          = role.lower().replace(" ", "")
    relevant_statuses = NOTIFY_RULES.get(role_key, [])

    pending_count = sum(
        1 for o in all_orders
        if to_str(o.get("status")).strip().lower() in relevant_statuses
    )

    if pending_count == 0:
        return

    label_map = {
        "cooking":          "waiting in the kitchen",
        "out for delivery": "waiting for delivery",
        "cooked":           "cooked & waiting",
        "delivered":        "newly delivered",
    }
    desc = " / ".join(
        label_map[s]
        for s in relevant_statuses
        if any(to_str(o.get("status")).strip().lower() == s for o in all_orders)
    )

    st.markdown(
        f"""
        <div style="
            background:linear-gradient(90deg,#fef3c7,#fde68a);
            border:1.5px solid #f59e0b; border-radius:10px;
            padding:12px 20px; margin-bottom:18px;
            display:flex; align-items:center; gap:12px;
            font-size:1rem; font-weight:600; color:#78350f;
        ">
            🔔 &nbsp; <b>{pending_count} order(s)</b>&nbsp;{desc}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
#  STATUS PILL
# ─────────────────────────────────────────────
STATUS_MAP = {
    "pending":          ("s-pending",   "⏳ Pending"),
    "cooking":          ("s-cooking",   "🔥 Cooking"),
    "cooked":           ("s-cooking",   "✅ Cooked"),
    "out for delivery": ("s-out",       "🛵 Out for Delivery"),
    "delivered":        ("s-delivered", "✅ Delivered"),
}

def fmt_status(s: str) -> str:
    s_low = (s or "").strip().lower()
    cls, label = STATUS_MAP.get(s_low, ("", s or "—"))
    return f"<span class='status-pill {cls}'>{label}</span>"


# ─────────────────────────────────────────────
#  SHARED SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar(role: str):
    role_lower = role.lower().replace(" ", "")
    badge_cls  = {
        "cashier": "badge-cashier", "chef": "badge-chef", "deliveryman": "badge-delivery",
    }.get(role_lower, "")
    with st.sidebar:
        st.markdown("## 🍽️ Restaurant Manager")
        st.markdown("---")
        st.markdown(f"**{st.session_state.user['name']}**")
        st.markdown(f"<span class='badge {badge_cls}'>{role}</span>", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🚪  Logout", use_container_width=True):
            clear_session()
            st.rerun()


# ─────────────────────────────────────────────
#  LOGIN PAGE
# ─────────────────────────────────────────────
def login_page():
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            "<h1 style='text-align:center;font-size:2.4rem;'>🍽️ Restaurant Manager</h1>"
            "<p style='text-align:center;color:#64748b;margin-bottom:2rem;'>Sign in to your dashboard</p>",
            unsafe_allow_html=True,
        )
        with st.form("login_form", clear_on_submit=False):
            name      = st.text_input("👤  Name",     placeholder="Enter your name")
            password  = st.text_input("🔒  Password", placeholder="Enter your password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            if not name or not password:
                st.warning("Please enter both name and password.")
            else:
                with st.spinner("Authenticating…"):
                    user = authenticate(name, password)
                if user:
                    st.session_state.user = user
                    save_session_to_params(user)
                    st.success(f"Welcome, {user['name']}! 🎉")
                    st.rerun()
                else:
                    st.error("Invalid name or password. Please try again.")


# ─────────────────────────────────────────────
#  CASHIER DASHBOARD
# ─────────────────────────────────────────────
def cashier_dashboard():
    st_autorefresh(interval=REFRESH_INTERVAL_MS, key="cashier_refresh")

    render_sidebar("Cashier")
    st.title("🧾 Cashier Dashboard")
    st.markdown("Manage and track all orders.")

    with st.spinner("Loading orders…"):
        orders = get_rows(TABLE_ORDERS)

    with st.spinner("Loading order items…"):
        items = get_rows(TABLE_ORDER_ITEMS)

    # 🔔 Notifications
    check_notifications("cashier", orders, all_items=items)
    render_notification_banner("cashier", orders)

    tab_orders, tab_items = st.tabs(["📋 Orders", "🛒 Order Items"])

    # ── Orders tab ───────────────────────────────────────────────
    with tab_orders:
        if not orders:
            st.info("No orders found.")
        else:
            # Drop: id, order (reverse-link float), order_items (link)
            df = clean_df(pd.DataFrame(orders), drop_cols=["id", "order", "order_items"])

            # Show only rows whose order_id starts with "ORD"
            if "order_id" in df.columns:
                df = df[df["order_id"].astype(str).str.startswith("ORD")]

            st.markdown(f"**{len(df)} order(s) found**")

            # Color the status column based on value
            _STATUS_COLORS = {
                "pending":          "background-color:#fef9c3; color:#713f12; font-weight:600;",
                "cooking":          "background-color:#ffedd5; color:#9a3412; font-weight:600;",
                "cooked":           "background-color:#d1fae5; color:#065f46; font-weight:600;",
                "out for delivery": "background-color:#ede9fe; color:#4c1d95; font-weight:600;",
                "delivered":        "background-color:#dcfce7; color:#166534; font-weight:600;",
            }
            def _color_status(val):
                return _STATUS_COLORS.get(str(val).strip().lower(), "")

            if "status" in df.columns:
                styled_df = df.style.map(_color_status, subset=["status"])
            else:
                styled_df = df.style

            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            st.markdown("### ⚡ Update Order Status")
            col_a, col_b = st.columns(2)

            # Use the ORD-xxx label for the selectbox, but keep the row id for the API call
            ord_orders   = [o for o in orders
                            if to_str(o.get("order_id")).startswith("ORD")]
            order_labels = {to_str(o.get("order_id")) or str(o["id"]): o["id"]
                            for o in ord_orders}

            with col_a:
                selected_cook_label = st.selectbox(
                    "Select Order →  Send to Chef",
                    list(order_labels.keys()), key="cook_sel"
                )
                if st.button("🔥  Send to Chef (Cooking)", use_container_width=True, type="primary"):
                    ok, err = update_row(TABLE_ORDERS, order_labels[selected_cook_label],
                                        {"status": "Cooking"})
                    if ok:
                        st.success(f"Order {selected_cook_label} → Cooking 🔥")
                        st.rerun()
                    else:
                        st.error(f"Update failed: {err}")

            with col_b:
                selected_del_label = st.selectbox(
                    "Select Order →  Send to Delivery",
                    list(order_labels.keys()), key="del_sel"
                )
                if st.button("🛵  Send to Delivery Man", use_container_width=True, type="primary"):
                    ok, err = update_row(TABLE_ORDERS, order_labels[selected_del_label],
                                        {"status": "Out for Delivery"})
                    if ok:
                        st.success(f"Order {selected_del_label} → Out for Delivery 🛵")
                        st.rerun()
                    else:
                        st.error(f"Update failed: {err}")

    # ── Order Items tab ──────────────────────────────────────────
    with tab_items:
        if not items:
            st.info("No order items found.")
        else:
            df_items = clean_df(pd.DataFrame(items))

            # Find the "Orders" linked column (shows ORD-xxx after clean_df resolves it)
            order_col = next(
                (c for c in df_items.columns if c.lower() == "orders"),
                None
            )

            # Rename Orders → order_id
            if order_col:
                df_items = df_items.rename(columns={order_col: "order_id"})

            # Drop: id, and any leftover order-like cols except our renamed one
            cols_to_drop = [
                c for c in df_items.columns
                if c.lower() in ("id", "order") or
                   (c.lower().startswith("order") and c != "order_id")
            ]
            df_items = df_items.drop(columns=cols_to_drop, errors="ignore")

            # Filter: only items linked to an ORD-xxx order
            if "order_id" in df_items.columns:
                df_items = df_items[
                    df_items["order_id"].astype(str).str.startswith("ORD")
                ]

            st.markdown(f"**{len(df_items)} item(s) found**")
            st.dataframe(df_items, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
#  CHEF DASHBOARD
# ─────────────────────────────────────────────
def chef_dashboard():
    st_autorefresh(interval=REFRESH_INTERVAL_MS, key="chef_refresh")

    render_sidebar("Chef")
    st.title("👨‍🍳 Chef Dashboard")
    st.markdown("Orders sent to the kitchen will appear here with their items.")

    with st.spinner("Loading orders…"):
        all_orders = get_rows(TABLE_ORDERS)

    check_notifications("chef", all_orders)
    render_notification_banner("chef", all_orders)

    cooking_orders = [
        o for o in all_orders
        if to_str(o.get("status")).strip().lower() == "cooking"
    ]

    if not cooking_orders:
        st.info("No orders in the kitchen queue yet.")
        return

    with st.spinner("Loading order items…"):
        all_items = get_rows(TABLE_ORDER_ITEMS)

    st.markdown(f"### 🔥 {len(cooking_orders)} order(s) to cook")

    for order in cooking_orders:
        oid         = order["id"]
        order_label = to_str(order.get("order_id")) or f"#{oid}"
        notes       = to_str(order.get("notes"))
        items       = [i for i in all_items if item_order_id(i) == oid]

        with st.expander(f"🧾 Order {order_label}", expanded=True):
            if notes:
                st.info(f"📝 Notes: {notes}")
            if items:
                rows = [
                    {
                        "Menu Item": resolve_link_field(
                            i.get("menu_item") or i.get("Menu Items") or i.get("menu_items") or ""
                        ),
                        "Quantity": i.get("quantity", ""),
                    }
                    for i in items
                ]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.warning("No items found for this order.")

    st.markdown("---")
    st.markdown("### ✅ Mark Order as Cooked")
    order_options  = {f"Order {to_str(o.get('order_id')) or o['id']}": o["id"] for o in cooking_orders}
    selected_label = st.selectbox("Select order to mark as done", list(order_options.keys()))
    selected_id    = order_options[selected_label]

    if st.button("✅  Cooked / Done — Notify Cashier", use_container_width=True, type="primary"):
        ok, err = update_row(TABLE_ORDERS, selected_id, {"status": "Cooked"})
        if ok:
            st.success(f"{selected_label} marked as Cooked! Cashier notified ✅")
            st.rerun()
        else:
            st.error(f"Update failed: {err}")


# ─────────────────────────────────────────────
#  DELIVERY MAN DASHBOARD
# ─────────────────────────────────────────────
def delivery_dashboard():
    st_autorefresh(interval=REFRESH_INTERVAL_MS, key="delivery_refresh")

    render_sidebar("Delivery Man")
    st.title("🛵 Delivery Man Dashboard")
    st.markdown("Orders assigned for delivery will appear here.")

    with st.spinner("Loading orders…"):
        all_orders = get_rows(TABLE_ORDERS)

    check_notifications("deliveryman", all_orders)
    render_notification_banner("deliveryman", all_orders)

    orders = [
        o for o in all_orders
        if to_str(o.get("status")).strip().lower() == "out for delivery"
    ]

    if not orders:
        st.info("No orders assigned for delivery yet.")
        return

    with st.spinner("Loading order items…"):
        all_items = get_rows(TABLE_ORDER_ITEMS)

    st.markdown(f"### 📦 {len(orders)} order(s) out for delivery")

    for order in orders:
        oid         = order["id"]
        order_label = to_str(order.get("order_id")) or f"#{oid}"
        customer    = to_str(order.get("customer_name")) or "—"
        phone       = to_str(order.get("phone"))         or "—"
        address     = to_str(order.get("address"))       or "—"
        total_price = to_str(order.get("total_price"))   or "—"
        items       = [i for i in all_items if item_order_id(i) == oid]

        with st.expander(f"📦 Order {order_label} — {customer}", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**👤 Customer:** {customer}")
                st.markdown(f"**📞 Phone:** {phone}")
                st.markdown(f"**📍 Address:** {address}")
            with col2:
                st.markdown(f"**🧾 Order ID:** `{order_label}`")
                st.markdown(f"**💰 Total Price:** {total_price}")
            st.markdown("---")
            if items:
                st.markdown("**🛒 Ordered Items**")
                rows = [
                    {
                        "Menu Item": resolve_link_field(
                            i.get("menu_item") or i.get("Menu Items") or i.get("menu_items") or ""
                        ),
                        "Quantity": i.get("quantity", "—"),
                    }
                    for i in items
                ]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.warning("No items found for this order.")

    st.markdown("---")
    st.markdown("### ✅ Mark Order as Delivered")
    order_options = {
        f"Order {to_str(o.get('order_id')) or o['id']} — {to_str(o.get('customer_name'))}": o["id"]
        for o in orders
    }
    selected_label = st.selectbox("Select order", list(order_options.keys()))
    selected_id    = order_options[selected_label]

    if st.button("📦  Delivered — Notify Cashier", use_container_width=True, type="primary"):
        ok, err = update_row(TABLE_ORDERS, selected_id, {"status": "Delivered"})
        if ok:
            st.success(f"{selected_label} marked as Delivered! 🎉")
            st.rerun()
        else:
            st.error(f"Update failed: {err}")


# ─────────────────────────────────────────────
#  ROUTER
# ─────────────────────────────────────────────
if st.session_state.user is None:
    login_page()
else:
    role = to_str(st.session_state.user.get("role")).strip().lower()
    if role == "cashier":
        cashier_dashboard()
    elif role in ("chef", "chief"):
        chef_dashboard()
    elif role in ("delivery man", "delivery", "deliveryman"):
        delivery_dashboard()
    else:
        st.error(f"Unknown role: '{role}'. Please contact your administrator.")
        if st.button("Logout"):
            clear_session()
            st.rerun()