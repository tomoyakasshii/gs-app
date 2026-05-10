import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# ── ファイルパス ──────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
CUSTOMERS_CSV = BASE_DIR / "customers.csv"
HISTORY_CSV   = BASE_DIR / "history.csv"

# ── CSV ロード / 保存 ─────────────────────────────────────────────────────────
def load_customers() -> pd.DataFrame:
    if not CUSTOMERS_CSV.exists():
        pd.DataFrame([
            {"plate": "1234", "name": "山田 太郎 様", "car": "トヨタ プリウス",
             "size": "195/65R15", "memo": "常連様。いつも洗車は撥水希望。ホイールの傷に注意。"},
            {"plate": "5678", "name": "佐藤 花子 様", "car": "ホンダ N-BOX",
             "size": "155/65R14", "memo": "半年前にタイヤ4本交換済み。空気圧高めを希望。"},
        ]).to_csv(CUSTOMERS_CSV, index=False)
    return pd.read_csv(CUSTOMERS_CSV, dtype=str).fillna("")

def load_history() -> pd.DataFrame:
    if not HISTORY_CSV.exists():
        pd.DataFrame([
            {"plate": "1234", "date": "2026/04/10", "type": "⛽️ 給油",       "note": "満タン。タイヤワックス無料実施。"},
            {"plate": "1234", "date": "2026/01/15", "type": "🔧 車検",       "note": "車検完了。次回オイル交換4月。"},
            {"plate": "1234", "date": "2025/11/20", "type": "🛞 タイヤ相談",  "note": "スタッドレス検討中とのこと。"},
        ]).to_csv(HISTORY_CSV, index=False)
    return pd.read_csv(HISTORY_CSV, dtype=str).fillna("")

def save_history(df: pd.DataFrame):
    df.to_csv(HISTORY_CSV, index=False)

def save_customer(plate: str, name: str, car: str, size: str, memo: str):
    df = load_customers()
    idx = df[df["plate"] == plate].index
    df.loc[idx, ["name", "car", "size", "memo"]] = [name, car, size, memo]
    df.to_csv(CUSTOMERS_CSV, index=False)

# ── ページ設定 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GS接客支援システム",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── セッションステート初期化 ──────────────────────────────────────────────────
defaults = {
    "digits": "",
    "searched_plate": "",
    "mode": "view",   # "view" | "edit" | "quote"
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── グローバル CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── 全体 ── */
.stApp,
[data-testid="stAppViewContainer"],
section[data-testid="stMain"] { background: #ffffff !important; }
[data-testid="stHeader"]       { background: #ffffff !important;
                                 border-bottom: 1px solid #f0f0f0; }
[data-testid="stSidebar"]      { display: none; }
html, body, [class*="css"] {
    font-family: 'Inter','Helvetica Neue',Arial,
                 'Hiragino Kaku Gothic ProN','Yu Gothic',sans-serif;
}
@media (max-width: 768px) {
    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        padding: 0.5rem !important;
    }
}

/* ── テンキー3列強制（3子要素を持つ横並びブロックのみ） ── */
[data-testid="stHorizontalBlock"]:has(
  > [data-testid="column"]:nth-child(3):last-child
) [data-testid="column"] {
    width: 31% !important;
    flex: 1 1 31% !important;
    min-width: 31% !important;
}

/* ── テンキーボタン ── */
[data-testid="stHorizontalBlock"]:has(
  > [data-testid="column"]:nth-child(3):last-child
) [data-testid="stButton"] > button {
    height: 72px !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    background: #f7f7f7 !important;
    border: 1.5px solid #e3e3e3 !important;
    border-radius: 14px !important;
    color: #1a1a2e !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
    padding: 0 !important;
    transition: background 0.08s, transform 0.08s !important;
}
[data-testid="stHorizontalBlock"]:has(
  > [data-testid="column"]:nth-child(3):last-child
) [data-testid="stButton"] > button:hover {
    background: #ebebeb !important;
}
[data-testid="stHorizontalBlock"]:has(
  > [data-testid="column"]:nth-child(3):last-child
) [data-testid="stButton"] > button:active {
    background: #d8d8d8 !important;
    transform: scale(0.94) !important;
}

/* ── Primary ボタン共通 ── */
[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
    background: #2563eb !important;
    border-color: #1d4ed8 !important;
    color: #ffffff !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    height: 52px !important;
    border-radius: 12px !important;
}
[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover {
    background: #1d4ed8 !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.3) !important;
}
/* 検索ボタンだけ高さを大きく */
[data-testid="stButton"]:has([data-testid="baseButton-primary"]) button {
    transition: all 0.1s !important;
}

/* ── 入力ディスプレイ ── */
.numpad-display {
    background: linear-gradient(135deg, #f9f9f9, #efefef);
    border: 1.5px solid #e0e0e0;
    border-radius: 16px;
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 10px;
}
.d-val { font-size: 2.5rem; font-weight: 800; letter-spacing: 0.5rem;
          color: #1a1a2e; font-variant-numeric: tabular-nums; }
.d-ph  { font-size: 1rem; color: #c8c8c8; letter-spacing: 0.4rem; }

/* ── 顧客カード ── */
.customer-card {
    padding: 20px 24px;
    border: 1px solid #ebebeb;
    border-radius: 16px;
    background: #fafafa;
    margin-bottom: 6px;
}
.customer-name   { font-size: 1.4rem; font-weight: 700; color: #111; margin-bottom: 10px; }
.customer-detail { font-size: 0.92rem; color: #444; margin: 5px 0; }
.customer-memo   {
    margin-top: 14px; padding: 10px 14px;
    background: #fff9ee;
    border-left: 4px solid #f0a500;
    border-radius: 0 8px 8px 0;
    font-size: 0.88rem; color: #6b4c00; line-height: 1.7;
}

/* ── フォームセクション ── */
.form-section {
    background: #fafafa;
    border: 1px solid #ebebeb;
    border-radius: 16px;
    padding: 22px 24px;
    margin-bottom: 12px;
}
.form-section-title {
    font-size: 0.8rem;
    font-weight: 700;
    color: #888;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 14px;
}

/* ── Notion風 入力フィールド ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
    background: #ffffff !important;
    border: 1.5px solid #e8e8e8 !important;
    border-radius: 10px !important;
    font-size: 0.95rem !important;
    padding: 10px 14px !important;
    color: #1a1a2e !important;
    transition: border-color 0.15s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
}
[data-testid="stSelectbox"] > div > div {
    border: 1.5px solid #e8e8e8 !important;
    border-radius: 10px !important;
}

/* ── 見積計算ボックス ── */
.calc-box {
    background: #f8faff;
    border: 1px solid #dbeafe;
    border-radius: 14px;
    padding: 18px 20px;
    margin-top: 6px;
}
.calc-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #e8eef8;
    font-size: 0.9rem;
    color: #444;
}
.calc-row:last-child { border-bottom: none; }
.calc-label { color: #666; }
.calc-value { font-weight: 600; color: #1a1a2e; }
.calc-total-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0 0 0;
    margin-top: 6px;
    border-top: 2px solid #bfdbfe;
    font-size: 1.25rem;
    font-weight: 800;
    color: #1d4ed8;
}

/* ── 履歴タイムライン ── */
.timeline-card {
    padding: 14px 20px; margin-bottom: 10px;
    border: 1px solid #ebebeb;
    border-left: 4px solid #4a90d9;
    border-radius: 0 14px 14px 0;
    background: #fff;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.timeline-date { font-size: 0.75rem; color: #aaa; margin-bottom: 3px; }
.timeline-type { font-size: 1rem; font-weight: 700; color: #1a1a2e; margin-bottom: 4px; }
.timeline-note { font-size: 0.85rem; color: #555; line-height: 1.7; }

.divider { border: none; border-top: 1px solid #f0f0f0; margin: 16px 0; }

/* ── 顧客バッジヘッダー ── */
.cust-header {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 14px;
}
.cust-header-name { font-size: 1.35rem; font-weight: 800; color: #111; }
.cust-header-car  { font-size: 0.9rem; color: #666; }
.cust-header-badge {
    background: #f0f0f0;
    color: #666;
    font-size: 0.75rem;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ── データ読み込み ────────────────────────────────────────────────────────────
customers_df = load_customers()
history_df   = load_history()

# ── タイトル ──────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='font-size:1.5rem;font-weight:800;color:#1a1a2e;margin-bottom:0'>"
    "⛽ GS 接客支援システム</h1>",
    unsafe_allow_html=True)
st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ── 2カラムレイアウト ─────────────────────────────────────────────────────────
left, right = st.columns([1, 2], gap="large")

# ═════════════════════════════════════════════════════════════════════════════
#  LEFT ── テンキー
# ═════════════════════════════════════════════════════════════════════════════
with left:
    st.markdown(
        "<p style='font-size:0.9rem;font-weight:700;color:#555;margin:0 0 8px 0'>"
        "🔢 車番入力（下4桁）</p>",
        unsafe_allow_html=True)

    _display_slot = st.empty()

    NUMPAD_ROWS = [
        [("7", "n7"), ("8", "n8"), ("9", "n9")],
        [("4", "n4"), ("5", "n5"), ("6", "n6")],
        [("1", "n1"), ("2", "n2"), ("3", "n3")],
        [("C", "nc"), ("⌫", "nd"), ("0", "n0")],
    ]

    for row in NUMPAD_ROWS:
        cols = st.columns(3)
        for col, (label, bkey) in zip(cols, row):
            with col:
                if st.button(label, key=bkey, use_container_width=True):
                    if label == "C":
                        st.session_state.digits = ""
                    elif label == "⌫":
                        st.session_state.digits = st.session_state.digits[:-1]
                    elif label.isdigit() and len(st.session_state.digits) < 4:
                        st.session_state.digits += label

                    if len(st.session_state.digits) == 4:
                        st.session_state.searched_plate = st.session_state.digits
                        st.session_state.digits = ""
                        st.session_state.mode = "view"

    if st.button("🔍  検索", key="nsearch", type="primary", use_container_width=True):
        st.session_state.searched_plate = st.session_state.digits
        st.session_state.digits = ""
        st.session_state.mode = "view"

    _d = st.session_state.digits
    _disp_html = (
        f'<div class="numpad-display"><span class="d-val">{_d}</span></div>'
        if _d else
        '<div class="numpad-display"><span class="d-ph">_&nbsp;&nbsp;_&nbsp;&nbsp;_&nbsp;&nbsp;_</span></div>'
    )
    _display_slot.markdown(_disp_html, unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
#  RIGHT ── 顧客情報 / 編集 / 見積
# ═════════════════════════════════════════════════════════════════════════════
with right:
    plate = st.session_state.searched_plate

    # ── 未検索 ────────────────────────────────────────────────────────────────
    if not plate:
        st.markdown("""
        <div style="padding:80px 32px;text-align:center;">
            <div style="font-size:3rem;margin-bottom:14px">🔍</div>
            <div style="font-size:0.95rem;color:#bbb;line-height:2">
                左のテンキーで車番下4桁を入力してください<br>
                <span style='color:#ccc;font-size:0.85rem'>4桁入力で自動検索 / または「検索」ボタン</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        match = customers_df[customers_df["plate"] == plate]

        # ── 顧客未登録 ────────────────────────────────────────────────────────
        if match.empty:
            st.error(f"車番「{plate}」の顧客データが見つかりません。")
            st.button("🆕 新規顧客として登録（実装予定）", use_container_width=True)

        # ── 顧客あり ──────────────────────────────────────────────────────────
        else:
            cust = match.iloc[0]
            mode = st.session_state.mode

            # ── 顧客ヘッダー（全モード共通）
            st.markdown(f"""
            <div class="cust-header">
                <span class="cust-header-name">{cust['name']}</span>
                <span class="cust-header-car">{cust['car']}</span>
                <span class="cust-header-badge">#{plate}</span>
            </div>
            """, unsafe_allow_html=True)

            # ── モードボタン（view時のみ）
            if mode == "view":
                ca, cb = st.columns(2)
                with ca:
                    if st.button("🛞 タイヤ見積を作成", use_container_width=True, key="go_quote"):
                        st.session_state.mode = "quote"
                        mode = "quote"
                with cb:
                    if st.button("✏️ 顧客情報を編集", use_container_width=True, key="go_edit"):
                        st.session_state.mode = "edit"
                        mode = "edit"

            st.markdown("<hr class='divider'>", unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════════════════
            #  VIEW モード
            # ══════════════════════════════════════════════════════════════════
            if mode == "view":
                # 顧客カード
                st.markdown(f"""
                <div class="customer-card">
                    <div class="customer-name">👤 {cust['name']}</div>
                    <div class="customer-detail">🚗 &nbsp;<b>車種：</b>{cust['car']}</div>
                    <div class="customer-detail">🛞 &nbsp;<b>タイヤサイズ：</b>{cust['size']}</div>
                    <div class="customer-memo">
                        ⚠️ &nbsp;<b>ベテランの伝言板</b><br>{cust['memo']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<hr class='divider'>", unsafe_allow_html=True)

                # 来店履歴
                st.markdown("### 📜 来店履歴")
                with st.expander("➕ 今日の来店を記録する"):
                    new_type = st.selectbox("来店目的", [
                        "⛽️ 給油", "🚿 洗車", "🔧 車検",
                        "🛢️ オイル交換", "🛞 タイヤ相談", "📋 その他",
                    ])
                    new_note = st.text_area("接客メモ", placeholder="気づいたことを記入…", key="hist_note")
                    if st.button("💾 記録を保存する", type="primary", use_container_width=True, key="save_hist"):
                        new_row = pd.DataFrame([{
                            "plate": plate,
                            "date":  datetime.now().strftime("%Y/%m/%d"),
                            "type":  new_type,
                            "note":  new_note,
                        }])
                        history_df = pd.concat([new_row, history_df], ignore_index=True)
                        save_history(history_df)
                        st.success("記録しました！")
                        st.rerun()

                plate_hist = history_df[history_df["plate"] == plate].copy()
                if plate_hist.empty:
                    st.markdown("""
                    <div style="padding:26px;text-align:center;color:#bbb;
                                border:1px dashed #e0e0e0;border-radius:12px;margin-top:10px;">
                        まだ来店履歴がありません
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    plate_hist["_dt"] = pd.to_datetime(
                        plate_hist["date"], format="%Y/%m/%d", errors="coerce"
                    )
                    plate_hist = plate_hist.sort_values("_dt", ascending=False)
                    for _, hrow in plate_hist.iterrows():
                        try:
                            delta = (datetime.now() - hrow["_dt"].to_pydatetime()).days
                            ago   = "今日" if delta == 0 else f"{delta}日前"
                        except Exception:
                            ago = ""
                        st.markdown(f"""
                        <div class="timeline-card">
                            <div class="timeline-date">{hrow['date']} &nbsp;·&nbsp; {ago}</div>
                            <div class="timeline-type">{hrow['type']}</div>
                            <div class="timeline-note">{hrow['note']}</div>
                        </div>
                        """, unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════════════════
            #  EDIT モード
            # ══════════════════════════════════════════════════════════════════
            elif mode == "edit":
                st.markdown(
                    "<div class='form-section-title'>✏️ 顧客情報を編集</div>",
                    unsafe_allow_html=True)

                with st.form("customer_edit_form"):
                    e_name = st.text_input("氏名", value=cust["name"])
                    e_car  = st.text_input("車種", value=cust["car"])
                    e_size = st.text_input("タイヤサイズ", value=cust["size"],
                                           placeholder="例: 195/65R15")
                    e_memo = st.text_area("ベテランの伝言板（メモ）", value=cust["memo"],
                                          height=120,
                                          placeholder="注意事項・要望・接客のコツなど")

                    sa, sb = st.columns(2)
                    with sa:
                        do_save   = st.form_submit_button("💾 保存する",
                                                          type="primary",
                                                          use_container_width=True)
                    with sb:
                        do_cancel = st.form_submit_button("キャンセル",
                                                          use_container_width=True)

                if do_save:
                    save_customer(plate, e_name, e_car, e_size, e_memo)
                    st.session_state.mode = "view"
                    st.success(f"顧客情報を更新しました。")
                    st.rerun()

                if do_cancel:
                    st.session_state.mode = "view"
                    st.rerun()

            # ══════════════════════════════════════════════════════════════════
            #  QUOTE モード
            # ══════════════════════════════════════════════════════════════════
            elif mode == "quote":
                st.markdown(
                    "<div class='form-section-title'>🛞 タイヤ見積作成</div>",
                    unsafe_allow_html=True)

                # ── 入力エリア
                q1, q2 = st.columns(2)
                with q1:
                    q_size  = st.text_input("タイヤサイズ", value=cust["size"], key="q_size")
                    q_brand = st.text_input("銘柄・商品名（任意）", key="q_brand",
                                            placeholder="例: ダンロップ ENASAVE")
                with q2:
                    q_qty   = st.selectbox("本数", [4, 2, 1], key="q_qty")
                    q_price = st.number_input("単価（1本・税抜）", min_value=0,
                                              value=15000, step=500, key="q_price",
                                              format="%d")

                q3, q4 = st.columns(2)
                with q3:
                    q_labor = st.number_input("工賃（1本・税抜）", min_value=0,
                                              value=2000, step=100, key="q_labor",
                                              format="%d")
                with q4:
                    q_disp  = st.number_input("廃タイヤ処理費（1本）", min_value=0,
                                              value=300, step=50, key="q_disp",
                                              format="%d")

                # ── 自動計算
                sub_tire   = q_price * q_qty
                sub_labor  = q_labor * q_qty
                sub_disp   = q_disp  * q_qty
                subtotal   = sub_tire + sub_labor + sub_disp
                tax_amt    = int(subtotal * 0.10)
                total      = subtotal + tax_amt

                # ── 計算明細ボックス
                st.markdown(f"""
                <div class="calc-box">
                    <div class="calc-row">
                        <span class="calc-label">🛞 タイヤ代
                            <span style="color:#aaa;font-size:0.8rem">
                                ¥{q_price:,} × {q_qty}本
                            </span>
                        </span>
                        <span class="calc-value">¥{sub_tire:,}</span>
                    </div>
                    <div class="calc-row">
                        <span class="calc-label">🔧 工賃
                            <span style="color:#aaa;font-size:0.8rem">
                                ¥{q_labor:,} × {q_qty}本
                            </span>
                        </span>
                        <span class="calc-value">¥{sub_labor:,}</span>
                    </div>
                    <div class="calc-row">
                        <span class="calc-label">♻️ 廃タイヤ処理
                            <span style="color:#aaa;font-size:0.8rem">
                                ¥{q_disp:,} × {q_qty}本
                            </span>
                        </span>
                        <span class="calc-value">¥{sub_disp:,}</span>
                    </div>
                    <div class="calc-row">
                        <span class="calc-label">税抜合計</span>
                        <span class="calc-value">¥{subtotal:,}</span>
                    </div>
                    <div class="calc-row">
                        <span class="calc-label">消費税（10%）</span>
                        <span class="calc-value">¥{tax_amt:,}</span>
                    </div>
                    <div class="calc-total-row">
                        <span>税込合計</span>
                        <span>¥{total:,}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.write("")
                q_note = st.text_area(
                    "見積メモ（任意）", key="q_note",
                    placeholder="お客様への説明・特記事項など",
                    height=80)

                qa, qb = st.columns(2)
                with qa:
                    if st.button("📋 履歴に保存する", type="primary",
                                 use_container_width=True, key="save_quote"):
                        brand_str = f"【{q_brand}】 " if q_brand else ""
                        note_str  = (
                            f"{brand_str}{q_size} / {q_qty}本 / "
                            f"税込 ¥{total:,}"
                            + (f"\n{q_note}" if q_note else "")
                        )
                        new_row = pd.DataFrame([{
                            "plate": plate,
                            "date":  datetime.now().strftime("%Y/%m/%d"),
                            "type":  "🛞 タイヤ見積",
                            "note":  note_str,
                        }])
                        history_df = pd.concat([new_row, history_df], ignore_index=True)
                        save_history(history_df)
                        st.success("見積を履歴に保存しました！")
                        st.session_state.mode = "view"
                        st.rerun()
                with qb:
                    if st.button("閉じる", use_container_width=True, key="close_quote"):
                        st.session_state.mode = "view"
                        st.rerun()
