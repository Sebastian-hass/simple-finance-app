import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="Simple Finance App", page_icon=":money_with_wings:", layout="wide")

category_file = "categories.json"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": []
    }

if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)

# 🔥 Asegúrarse que siempre esté "Uncategorized"
if "Uncategorized" not in st.session_state.categories:
    st.session_state.categories["Uncategorized"] = []

def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)

def categorize_transaction(df):
    df["Category"] = "Uncategorized"

    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue

        lowered_keywords = [keyword.lower().strip() for keyword in keywords]

        for idx, row in df.iterrows():
            details = row["Concepto"].lower().strip()
            if details in lowered_keywords:
                df.at[idx, "Category"] = category
    return df

def load_transactions(file):
    try:
        df = pd.read_csv(file, delimiter=";")
        df.column = [col.strip() for col in df.columns]
        # 🔥 Limpiamo y convertimo Importe y Saldo
        df["Importe"] = (
            df["Importe"]
            .str.replace(".", "", regex=False)   # Quita los puntos de miles
            .str.replace(",", ".", regex=False)  # Cambia coma decimal a punto decimal
            .str.replace("EUR", "", regex=False) # Borra 'EUR' si aún existe
            .str.strip()
            .astype(float)
        )

        df["Saldo"] = (
            df["Saldo"]
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.replace("EUR", "", regex=False)
            .str.strip()
            .astype(float)
        )

        df["Fecha"] = pd.to_datetime(df["Fecha"], format="%d/%m/%Y")

        return categorize_transaction(df)
    except Exception as e:
        st.error(f"Error when opening the file: {str(e)}")
        return None

def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    
    return False

def main():
    st.title("A Simple Finance Dashboard")

    uploaded_file = st.file_uploader("Upload your transactions in a CSV file", type=["csv"])

    if uploaded_file is not None:
        df = load_transactions(uploaded_file)

        if df is not None:
            debits_df = df[df["Importe"] < 0].copy()
            credits_df = df[df["Importe"] > 0].copy()

            st.session_state.debits_df = debits_df.copy()

            tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"])
            with tab1:
                new_category = st.text_input("New Category")
                add_button = st.button("Add Category")

                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()

                st.subheader("Your Expenses")
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Fecha", "Concepto", "Importe", "Saldo", "Category"]],
                    column_config={
                        "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                        "Importe": st.column_config.NumberColumn("Importe", format="%.2f €"),
                        "Saldo": st.column_config.NumberColumn("Saldo", format="%.2f €"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor",
                )

                save_button = st.button("Apply Changes")
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        if new_category == st.session_state.debits_df.at[idx, "Category"]:
                            continue

                        details = row["Concepto"]
                        st.session_state.debits_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, details)

                st.subheader('Expenses Summary')
                category_totals = st.session_state.debits_df.groupby("Category")["Importe"].sum().reset_index()
                category_totals["Importe"] = category_totals["Importe"].abs() 
                category_totals = category_totals.sort_values("Importe", ascending=False)
                
                st.write("DEBUG - CATEGORY TOTALS")
                st.dataframe(category_totals)  #para ver qué contiene realmente
                
                if not category_totals.empty:
                    fig = px.pie(
                        category_totals,
                        values="Importe",
                        names="Category",
                        title="Expenses by Category"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay datos para mostrar en el gráfico de categorías.")

                
            with tab2:
                st.subheader("Payments Summary")
                total_payments = credits_df["Importe"].sum()
                st.metric("Total Payments", f"{total_payments:,.2f} €")
                st.write(credits_df)

main()