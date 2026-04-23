# 🍽️ AI-Powered Restaurant Management System

An end-to-end restaurant orchestration system that integrates an **AI Agent** for customer ordering via chat, a **No-Code Database** for real-time data persistence, and a **Multi-Role Dashboard** for operational management.

---

## 🏗️ System Architecture

The project consists of three core components:

1.  **AI Workflow Engine (n8n):**
    * **Agentic Logic:** Uses an AI Agent node powered by **Azure OpenAI (GPT-4o)**.
    * **Tool Calling:** The agent is equipped with specialized tools to interact with the database:
        * `get_menu_items`: Fetches the latest menu from Baserow.
        * `create_order` & `create_order_item`: Generates new entries when a customer orders.
        * `update_order` & `update_order_item`: Modifies existing records based on user requests.
    * **Memory:** Integrated memory allows the agent to maintain context during a conversation.

2.  **Database (Baserow):**
    * Serves as the **Single Source of Truth** via a REST API.
    * **Tables:**
        * `Users`: Management of staff credentials and roles.
        * `Orders`: Tracking customer details, total prices, and status (Pending, Cooking, etc.).
        * `Order Items`: Granular list of items per order linked to the main Orders table.

3.  **Staff Dashboard (Streamlit):**
    * A Python-based web app with role-based access control.
    * **Features:** Real-time auto-refresh (every 30s), status-based UI color coding, and push notifications via `st.toast`.

---

## 🛠️ Tech Stack

* **Orchestration:** [n8n](https://n8n.io/)
* **Database:** [Baserow](https://baserow.io/)
* **AI Model:** Azure OpenAI (gpt-4.1-mini)
* **Dashboard:** [Streamlit](https://streamlit.io/)
* **Language:** Python 3.x

---

## 🚀 Role-Based Features

### 🧾 Cashier Dashboard
* **Order Oversight:** View all incoming orders and specific order items.
* **Workflow Control:** Manually push orders to the kitchen (`Cooking`) or to the delivery fleet (`Out for Delivery`).
* **Real-time Alerts:** Notified immediately when the AI Agent creates a new order or when a Chef completes a task.

### 👨‍🍳 Chef Dashboard
* **Kitchen Queue:** View a focused list of "Cooking" orders.
* **Ingredient Focus:** Expand orders to see specific items and quantities.
* **Completion:** One-click update to mark an order as `Cooked`, notifying the Cashier.

### 🛵 Delivery Dashboard
* **Logistics:** Access customer names, phone numbers, and delivery addresses.
* **Order Tracking:** View itemized lists to ensure order accuracy before departure.
* **Handover:** Mark orders as `Delivered` to close the lifecycle.

---

## ⚙️ Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/yourusername/restaurant-ai-manager.git](https://github.com/yourusername/restaurant-ai-manager.git)
    cd restaurant-ai-manager
    ```

2.  **Install Dependencies:**
    ```bash
    pip install streamlit requests pandas streamlit-autorefresh
    ```

3.  **Configure API Keys:**
    * In `app.py`, update the `API_TOKEN` and Table IDs (`TABLE_USERS`, `TABLE_ORDERS`, `TABLE_ORDER_ITEMS`) with your Baserow credentials.
    * Import the provided n8n JSON workflow into your n8n instance and connect your Azure OpenAI credentials.

4.  **Run the Dashboard:**
    ```bash
    streamlit run app.py
    ```

---

## 💡 How It Works (Example Flow)

1.  **Customer:** *"I want to order 2 Grilled Chickens and a Cola to Giza."*
2.  **n8n AI Agent:** Recognizes the intent, checks the menu via `get_menu_items`, and executes `create_order` in Baserow.
3.  **Cashier:** Sees the new order appear instantly on the dashboard.
4.  **Chef:** Receives the order in the kitchen queue after the Cashier approves it.
5.  **Delivery:** Once cooked, the delivery person gets the address details and completes the fulfillment.

---

**Developed by Saif Hossam**
*AI Engineer specialized in RAG Systems & Workflow Automation.*
