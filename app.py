import datetime
import sqlite3
import pandas as pd
import streamlit as st

# --- データベース初期化 ---
DB_FILE = "meal_schedule.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 予定テーブル
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS schedule (
            date TEXT,
            user_name TEXT,
            lunch TEXT,
            dinner TEXT,
            PRIMARY KEY (date, user_name)
        )
    """
    )
    # メンバー管理テーブル
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS members (
            name TEXT PRIMARY KEY
        )
    """
    )

    # 初回起動時のみデフォルトメンバーを登録
    c.execute("SELECT COUNT(*) FROM members")
    if c.fetchone()[0] == 0:
        default_members = [("お父さん",), ("お母さん",), ("たろう",), ("はなこ",)]
        c.executemany("INSERT INTO members VALUES (?)", default_members)

    conn.commit()
    conn.close()


def load_members():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name FROM members ORDER BY rowid ASC")
    members = [row[0] for row in c.fetchall()]
    conn.close()
    return members


def add_member(name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO members VALUES (?)", (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()


def remove_member(name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM members WHERE name = ?", (name,))
    c.execute("DELETE FROM schedule WHERE user_name = ?", (name,))
    conn.commit()
    conn.close()


def load_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT date, user_name, lunch, dinner FROM schedule ORDER BY date ASC, user_name ASC",
        conn,
    )
    conn.close()
    return df


def save_data(date_str, user_name, lunch, dinner):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO schedule (date, user_name, lunch, dinner)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(date, user_name) DO UPDATE SET
            lunch=excluded.lunch,
            dinner=excluded.dinner
    """,
        (date_str, user_name, lunch, dinner),
    )
    conn.commit()
    conn.close()


def delete_data(date_str, user_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "DELETE FROM schedule WHERE date = ? AND user_name = ?",
        (date_str, user_name),
    )
    conn.commit()
    conn.close()


# DB初期化
init_db()

st.set_page_config(
    page_title="家族の食事要否カレンダー", layout="wide", page_icon="🍱"
)
st.title("🍱 家族の食事要否確認・ピックアップ")

# 登録メンバー取得
family_members = load_members()

# --- サイドバー：登録・更新フォーム ---
st.sidebar.header("✏️ 予定の入力・変更")
if family_members:
    selected_user = st.sidebar.selectbox("名前を選択", family_members)
    selected_date = st.sidebar.date_input("日付を選択", datetime.date.today())

    lunch_option = st.sidebar.radio("昼食", ["必要", "不要"], index=0, key="lunch")
    dinner_option = st.sidebar.radio("夕食", ["必要", "不要"], index=0, key="dinner")

    if st.sidebar.button("保存・更新", type="primary"):
        date_str = selected_date.strftime("%Y-%m-%d")
        save_data(date_str, selected_user, lunch_option, dinner_option)
        st.sidebar.success(f"✅ {date_str}（{selected_user}）の予定を更新しました！")
        st.rerun()
else:
    st.sidebar.warning("メンバーが登録されていません。「👨‍👩‍👧‍👦 メンバー管理」タブから登録してください。")

# --- メインエリア ---
df = load_data()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "👀 ご飯が必要な人",
        "📅 マトリックス表",
        "📋 全データ一覧",
        "👨‍👩‍👧‍👦 メンバー管理",
        "🗑️ 予定の削除",
    ]
)

# --- タブ1：ピックアップ ---
with tab1:
    st.subheader("💡 ご飯が必要な人だけの確認")
    view_date = st.date_input("確認したい日付を選択", datetime.date.today(), key="view_date")
    target_date = view_date.strftime("%Y-%m-%d")

    st.markdown(f"#### 📅 {target_date} の食事状況")

    if not df.empty:
        day_df = df[df["date"] == target_date]
        lunch_needed = day_df[day_df["lunch"] == "必要"]["user_name"].tolist()
        dinner_needed = day_df[day_df["dinner"] == "必要"]["user_name"].tolist()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### ☀️ 昼食が必要な人")
            if lunch_needed:
                st.info(f"**合計 {len(lunch_needed)} 名**： " + "、 ".join(lunch_needed))
            else:
                st.write("昼食が必要な人はいません。")

        with col2:
            st.markdown("### 🌙 夕食が必要な人")
            if dinner_needed:
                st.success(f"**合計 {len(dinner_needed)} 名**： " + "、 ".join(dinner_needed))
            else:
                st.write("夕食が必要な人はいません。")
    else:
        st.info("データがありません。サイドバーから登録してください。")

# --- タブ2：マトリックス表 ---
with tab2:
    st.subheader("日付 × メンバー別 一覧表")
    if not df.empty:
        df["食事内容"] = "昼:" + df["lunch"] + " / 夕:" + df["dinner"]
        pivot_df = df.pivot(index="date", columns="user_name", values="食事内容").fillna("-")
        pivot_df.index.name = "日付"
        st.dataframe(pivot_df, use_container_width=True)
    else:
        st.info("データがありません。")

# --- タブ3：全リスト ---
with tab3:
    st.subheader("登録済みデータ一覧")
    if not df.empty:
        display_df = df.rename(columns={"date": "日付", "user_name": "名前", "lunch": "昼食", "dinner": "夕食"})
        st.dataframe(display_df[["日付", "名前", "昼食", "夕食"]], use_container_width=True, hide_index=True)
    else:
        st.info("データがありません。")

# --- タブ4：メンバー管理 ---
with tab4:
    st.subheader("👨‍👩‍👧‍👦 家族メンバーの追加・削除")
    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.markdown("#### ➕ メンバー追加")
        new_member = st.text_input("追加したい名前を入力")
        if st.button("メンバーを追加"):
            if new_member.strip():
                add_member(new_member.strip())
                st.success(f"「{new_member.strip()}」を追加しました！")
                st.rerun()
            else:
                st.error("名前を入力してください。")

    with col_m2:
        st.markdown("#### ➖ メンバー削除")
        if family_members:
            del_member = st.selectbox("削除したいメンバーを選択", family_members, key="del_mem_select")
            if st.button("メンバーを削除"):
                remove_member(del_member)
                st.warning(f"「{del_member}」と関連する予定データを削除しました。")
                st.rerun()
        else:
            st.info("削除できるメンバーがいません。")

    st.markdown("---")
    st.markdown("**現在の登録メンバー:** " + ", ".join(family_members))

# --- タブ5：予定の削除 ---
with tab5:
    st.subheader("登録済み予定の削除")
    if not df.empty:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            del_date = st.date_input("削除したい日付", datetime.date.today())
        with col_d2:
            del_user = st.selectbox("削除したいメンバー", family_members if family_members else ["なし"])

        del_date_str = del_date.strftime("%Y-%m-%d")
        if st.button("指定した予定を削除"):
            delete_data(del_date_str, del_user)
            st.success(f"{del_date_str} の {del_user} の予定を削除しました。")
            st.rerun()
    else:
        st.info("削除対象のデータがありません。")
