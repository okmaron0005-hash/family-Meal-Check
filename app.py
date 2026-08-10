import calendar
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

    # 初回起動時にご指定の5名を初期登録
    c.execute("SELECT COUNT(*) FROM members")
    if c.fetchone()[0] == 0:
        default_members = [
            ("かずのり",),
            ("ひろこ",),
            ("はるき",),
            ("ゆい",),
            ("りな",),
        ]
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
st.title("🍱 家族のご飯要否チェック")

# 登録メンバー取得
family_members = load_members()

# --- 最上部：かんたんご飯要否入力エリア ---
st.subheader("✏️ ご飯の要否を入力する")
if family_members:
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])

        with col1:
            selected_user = st.selectbox("名前", family_members)
        with col2:
            selected_date = st.date_input("日付", datetime.date.today())
        with col3:
            lunch_option = st.radio(
                "昼食", ["必要", "不要"], index=0, horizontal=True, key="lunch"
            )
        with col4:
            dinner_option = st.radio(
                "夕食", ["必要", "不要"], index=0, horizontal=True, key="dinner"
            )
        with col5:
            st.write("")  # 位置調整用の空行
            st.write("")
            if st.button("登録・保存", type="primary", use_container_width=True):
                date_str = selected_date.strftime("%Y-%m-%d")
                save_data(date_str, selected_user, lunch_option, dinner_option)
                st.success(
                    f"✅ {date_str}（{selected_user}）の予定を更新しました！"
                )
                st.rerun()
else:
    st.warning("メンバーが登録されていません。「👨‍👩‍👧‍👦 メンバー管理」タブから登録してください。")

st.markdown("---")

# --- メインエリア ---
df = load_data()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📆 月間カレンダー表示",
        "👀 指定日の「必要」な人",
        "📅 表で一覧表示",
        "👨‍👩‍👧‍👦 メンバー管理",
        "🗑️ 予定の削除",
    ]
)

# --- タブ1：月間カレンダー表示 ---
with tab1:
    st.subheader("📆 月間カレンダー（ご飯が必要な人一覧）")

    today = datetime.date.today()
    c1, c2 = st.columns(2)
    with c1:
        year = st.number_input("年", min_value=2024, max_value=2100, value=today.year)
    with c2:
        month = st.number_input("月", min_value=1, max_value=12, value=today.month)

    # 当月の日数を取得
    cal = calendar.monthcalendar(year, month)

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                day_df = df[df["date"] == date_str] if not df.empty else pd.DataFrame()

                lunch_needed = (
                    day_df[day_df["lunch"] == "必要"]["user_name"].tolist()
                    if not day_df.empty
                    else []
                )
                dinner_needed = (
                    day_df[day_df["dinner"] == "必要"]["user_name"].tolist()
                    if not day_df.empty
                    else []
                )

                box_content = f"**{day}日**\n"
                if lunch_needed:
                    box_content += f"☀️昼: {', '.join(lunch_needed)}\n"
                if dinner_needed:
                    box_content += f"🌙夕: {', '.join(dinner_needed)}\n"

                with cols[i]:
                    with st.container(border=True):
                        st.markdown(box_content)

# --- タブ2：指定日の「必要」な人ピックアップ ---
with tab2:
    st.subheader("💡 指定日の「ご飯が必要な人」")
    view_date = st.date_input(
        "確認したい日付を選択", datetime.date.today(), key="view_date"
    )
    target_date = view_date.strftime("%Y-%m-%d")

    st.markdown(f"#### 📅 {target_date} の状況")

    if not df.empty:
        day_df = df[df["date"] == target_date]
        lunch_needed = day_df[day_df["lunch"] == "必要"]["user_name"].tolist()
        dinner_needed = day_df[day_df["dinner"] == "必要"]["user_name"].tolist()

        col_l, col_d = st.columns(2)
        with col_l:
            st.markdown("### ☀️ 昼食が必要な人")
            if lunch_needed:
                st.info(
                    f"**合計 {len(lunch_needed)} 名**： "
                    + "、 ".join(lunch_needed)
                )
            else:
                st.write("昼食が必要な人はいません。")

        with col_d:
            st.markdown("### 🌙 夕食が必要な人")
            if dinner_needed:
                st.success(
                    f"**合計 {len(dinner_needed)} 名**： "
                    + "、 ".join(dinner_needed)
                )
            else:
                st.write("夕食が必要な人はいません。")
    else:
        st.info("登録データがありません。上部のフォームから入力してください。")

# --- タブ3：マトリックス表 ---
with tab3:
    st.subheader("日付 × メンバー別 一覧表")
    if not df.empty:
        df["食事内容"] = (
            "昼:" + df["lunch"] + " / 夕:" + df["dinner"]
        )
        pivot_df = df.pivot(
            index="date", columns="user_name", values="食事内容"
        ).fillna("-")
        pivot_df.index.name = "日付"
        st.dataframe(pivot_df, use_container_width=True)
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
            del_member = st.selectbox(
                "削除したいメンバーを選択",
                family_members,
                key="del_mem_select",
            )
            if st.button("メンバーを削除"):
                remove_member(del_member)
                st.warning(
                    f"「{del_member}」と関連する予定データを削除しました。"
                )
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
            del_user = st.selectbox(
                "削除したいメンバー",
                family_members if family_members else ["なし"],
            )

        del_date_str = del_date.strftime("%Y-%m-%d")
        if st.button("指定した予定を削除"):
            delete_data(del_date_str, del_user)
            st.success(f"{del_date_str} の {del_user} の予定を削除しました。")
            st.rerun()
    else:
        st.info("削除対象のデータがありません。")
