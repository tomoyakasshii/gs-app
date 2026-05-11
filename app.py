import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import re

BASE_DIR    = Path(__file__).parent
HISTORY_CSV = BASE_DIR / "history.csv"

# ── マスターデータ ─────────────────────────────────────────────────────────────
PURPOSE_OPTIONS   = ["給油","燃料券","洗車","オイル交換","バッテリー交換","タイヤ見積","タイヤ交換","車検見積","車検","その他"]
CUST_TYPE_OPTIONS = ["一般","業者","常連"]
PLATE_AREAS = [
    "(未選択)",
    "札幌","函館","旭川","釧路","帯広","北見","室蘭","苫小牧",
    "青森","八戸","盛岡","仙台","秋田","山形","福島","郡山","いわき",
    "水戸","土浦","宇都宮","那須","高崎","熊谷","大宮","川越","春日部","所沢","越谷","川口",
    "習志野","千葉","柏","市川","成田","袖ヶ浦",
    "品川","足立","練馬","多摩","八王子","相模","横浜","川崎","湘南","横須賀","平塚",
    "新潟","長岡","富山","石川","福井","長野","松本","諏訪",
    "静岡","浜松","沼津","富士山",
    "名古屋","岡崎","豊田","春日井","三河","一宮","岐阜","三重","四日市",
    "滋賀","京都","大阪","なにわ","和泉","堺","神戸","姫路","尼崎","奈良","和歌山",
    "鳥取","島根","岡山","広島","福山","山口",
    "徳島","香川","愛媛","高知",
    "福岡","北九州","久留米","佐賀","長崎","熊本","大分","宮崎","鹿児島","沖縄",
]
MAKER_OPTIONS = ["(未選択)","トヨタ","レクサス","ホンダ","日産","マツダ","スバル","スズキ","ダイハツ","三菱","メルセデス","BMW","アウディ","VW","ボルボ","ジャガー","ランドローバー","その他"]
COLOR_OPTIONS = ["(未選択)","ホワイト","パールホワイト","シルバー","ガンメタ","ブラック","グレー","ネイビー","ブルー","レッド","ピンク","グリーン","ゴールド","ブラウン","ベージュ","オレンジ","その他"]
AGE_OPTIONS   = ["(未選択)","10代","20代","30代","40代","50代","60代","70代","80代以上"]
GENDER_OPTIONS = ["無記名","男","女"]
TIRE_MAKER_OPTIONS = ["(未選択)","ブリヂストン","ヨコハマ","ダンロップ","トーヨー","住友(ファルケン)","ミシュラン","コンチネンタル","ピレリ","グッドイヤー","ハンコック","ネクセン","その他"]
KANA_OPTIONS  = ["(未選択)"] + list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん")

HISTORY_COLS = [
    "date","purpose","cust_type",
    "plate_area","plate_3digit","plate_kana","plate_num",
    "maker","car_model","color",
    "age","gender",
    "tire_size","tire_size_num","tire_year","tire_maker","tire_product",
    "memo",
]

def load_history() -> pd.DataFrame:
    if not HISTORY_CSV.exists():
        df = pd.DataFrame(columns=HISTORY_COLS)
        df.to_csv(HISTORY_CSV, index=False)
        return df
    df = pd.read_csv(HISTORY_CSV, dtype=str).fillna("")
    # 旧フォーマット (plate, type, note) → 新フォーマットへ移行
    if "plate" in df.columns and "plate_num" not in df.columns:
        df["plate_num"] = df["plate"]
    if "type" in df.columns and "purpose" not in df.columns:
        df["purpose"] = df["type"].str.replace(r"^[\S]+\s+", "", regex=True)
    if "note" in df.columns and "memo" not in df.columns:
        df["memo"] = df["note"]
    for col in HISTORY_COLS:
        if col not in df.columns:
            df[col] = ""
    return df[HISTORY_COLS]

def save_history(df: pd.DataFrame):
    df[HISTORY_COLS].to_csv(HISTORY_CSV, index=False)

def tire_to_num(s: str) -> str:
    return re.sub(r"[^\d]", "", s)

def opt(val: str) -> str:
    return "" if val == "(未選択)" else val

# ── ページ設定 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GS接客支援システム",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

defaults = {
    "digits": "",
    "searched_plate": None,   # None=初期, ""=全件, "1234"=絞り込み
    "mode": "list",           # "list" | "new_record" | "view_record"
    "view_idx": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.stApp,[data-testid="stAppViewContainer"],section[data-testid="stMain"]{background:#fff!important;}
[data-testid="stHeader"]{background:#fff!important;border-bottom:1px solid #f0f0f0;}
[data-testid="stSidebar"]{display:none;}
html,body,[class*="css"]{font-family:'Inter','Helvetica Neue',Arial,'Hiragino Kaku Gothic ProN','Yu Gothic',sans-serif;}
@media(max-width:768px){.main .block-container,[data-testid="stMainBlockContainer"]{padding:0.4rem!important;}}

/* ── テンキー列強制 */
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(3):last-child) [data-testid="column"]{
    width:31%!important;flex:1 1 31%!important;min-width:31%!important;}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(3):last-child) [data-testid="stButton"]>button{
    height:66px!important;font-size:1.4rem!important;font-weight:700!important;
    background:#f7f7f7!important;border:1.5px solid #e3e3e3!important;border-radius:14px!important;
    color:#1a1a2e!important;box-shadow:0 1px 4px rgba(0,0,0,.06)!important;padding:0!important;
    transition:background .08s,transform .08s!important;}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(3):last-child) [data-testid="stButton"]>button:hover{background:#ebebeb!important;}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(3):last-child) [data-testid="stButton"]>button:active{background:#d8d8d8!important;transform:scale(.94)!important;}

/* ── Primaryボタン */
[data-testid="stButton"]>button[data-testid="baseButton-primary"]{
    background:#2563eb!important;border-color:#1d4ed8!important;color:#fff!important;
    font-weight:700!important;height:50px!important;border-radius:12px!important;}
[data-testid="stButton"]>button[data-testid="baseButton-primary"]:hover{
    background:#1d4ed8!important;box-shadow:0 4px 14px rgba(37,99,235,.3)!important;}

/* ── 入力ディスプレイ */
.numpad-display{background:linear-gradient(135deg,#f9f9f9,#efefef);border:1.5px solid #e0e0e0;
    border-radius:16px;height:66px;display:flex;align-items:center;justify-content:center;margin-bottom:10px;}
.d-val{font-size:2.2rem;font-weight:800;letter-spacing:.5rem;color:#1a1a2e;font-variant-numeric:tabular-nums;}
.d-ph{font-size:1rem;color:#c8c8c8;letter-spacing:.4rem;}

/* ── フィールド */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input{
    background:#fff!important;border:1.5px solid #e8e8e8!important;border-radius:10px!important;
    font-size:.92rem!important;color:#1a1a2e!important;transition:border-color .15s!important;}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus{
    border-color:#2563eb!important;box-shadow:0 0 0 3px rgba(37,99,235,.12)!important;}
[data-testid="stSelectbox"]>div>div{border:1.5px solid #e8e8e8!important;border-radius:10px!important;}

/* ── バッジ */
.badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:.73rem;font-weight:600;}
.bp{background:#e0f2fe;color:#0369a1;}
.bt-一般{background:#f1f5f9;color:#64748b;}
.bt-業者{background:#fef3c7;color:#92400e;}
.bt-常連{background:#d1fae5;color:#065f46;}
.bg-男{background:#dbeafe;color:#1d4ed8;}
.bg-女{background:#fce7f3;color:#9d174d;}
.bg-無記名{background:#f1f5f9;color:#94a3b8;}

/* ── Notion風テーブル */
.tbl-wrap{overflow-x:auto;margin-top:8px;}
.notion-tbl{width:100%;border-collapse:collapse;min-width:720px;}
.notion-tbl thead tr{border-bottom:2px solid #e8e8e8;}
.notion-tbl th{padding:9px 10px;text-align:left;color:#aaa;font-size:.72rem;font-weight:700;letter-spacing:.05em;white-space:nowrap;}
.notion-tbl tbody tr{border-bottom:1px solid #f2f2f2;}
.notion-tbl td{padding:10px 10px;vertical-align:middle;font-size:.84rem;color:#1a1a2e;white-space:nowrap;}
.notion-tbl td.memo-cell{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:180px;color:#888;font-size:.78rem;}

/* ── 詳細カード */
.detail-card{background:#fafafa;border:1px solid #ebebeb;border-radius:16px;padding:22px 24px;margin-bottom:12px;}
.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 28px;font-size:.88rem;margin-top:12px;}
.detail-label{color:#aaa;font-size:.75rem;display:block;margin-bottom:2px;}
.detail-val{color:#1a1a2e;font-weight:500;}
.memo-box{margin-top:14px;padding:10px 14px;background:#fff9ee;border-left:4px solid #f0a500;
    border-radius:0 8px 8px 0;font-size:.86rem;color:#6b4c00;line-height:1.75;}

.divider{border:none;border-top:1px solid #f0f0f0;margin:12px 0;}
.sec-title{font-size:.73rem;font-weight:700;color:#aaa;letter-spacing:.08em;text-transform:uppercase;margin:16px 0 6px;}
</style>
""", unsafe_allow_html=True)

# ── タイトル ──────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='font-size:1.45rem;font-weight:800;color:#1a1a2e;margin-bottom:0'>⛽ GS 接客支援システム</h1>",
    unsafe_allow_html=True)
st.markdown("<hr class='divider'>", unsafe_allow_html=True)

left, right = st.columns([1, 2.4], gap="large")

# ═══════════════════════════════════════════════════════════════════════════════
#  LEFT ── テンキー
# ═══════════════════════════════════════════════════════════════════════════════
with left:
    st.markdown(
        "<p style='font-size:.88rem;font-weight:700;color:#555;margin:0 0 8px 0'>🔢 車番下4桁で検索</p>",
        unsafe_allow_html=True)
    _slot = st.empty()

    KEYS = [("7","n7"),("8","n8"),("9","n9"),
            ("4","n4"),("5","n5"),("6","n6"),
            ("1","n1"),("2","n2"),("3","n3"),
            ("C","nc"),("⌫","nd"),("0","n0")]

    for i in range(0, 12, 3):
        cols = st.columns(3)
        for col, (label, key) in zip(cols, KEYS[i:i+3]):
            with col:
                if st.button(label, key=key, use_container_width=True):
                    if label == "C":
                        st.session_state.digits = ""
                    elif label == "⌫":
                        st.session_state.digits = st.session_state.digits[:-1]
                    elif label.isdigit() and len(st.session_state.digits) < 4:
                        st.session_state.digits += label
                    if len(st.session_state.digits) == 4:
                        st.session_state.searched_plate = st.session_state.digits
                        st.session_state.digits = ""
                        st.session_state.mode = "list"
                        st.session_state.view_idx = None

    if st.button("🔍  検索", key="nsearch", type="primary", use_container_width=True):
        st.session_state.searched_plate = st.session_state.digits  # ""なら全件
        st.session_state.digits = ""
        st.session_state.mode = "list"
        st.session_state.view_idx = None

    _d = st.session_state.digits
    _slot.markdown(
        f'<div class="numpad-display"><span class="d-val">{_d}</span></div>' if _d else
        '<div class="numpad-display"><span class="d-ph">_ &nbsp;_ &nbsp;_ &nbsp;_</span></div>',
        unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    if st.button("➕ 新規来店記録", use_container_width=True, key="btn_new"):
        st.session_state.mode = "new_record"
        st.session_state.view_idx = None

# ═══════════════════════════════════════════════════════════════════════════════
#  RIGHT
# ═══════════════════════════════════════════════════════════════════════════════
with right:
    pq   = st.session_state.searched_plate
    mode = st.session_state.mode

    # ────────────────────── 初期画面 ──────────────────────────────────────────
    if pq is None and mode not in ("new_record", "view_record"):
        st.markdown("""
        <div style="padding:70px 32px;text-align:center;">
            <div style="font-size:3rem;margin-bottom:14px">🔍</div>
            <div style="font-size:.92rem;color:#bbb;line-height:2.4">
                左のテンキーで車番下4桁を入力<br>
                <span style='color:#ccc;font-size:.8rem'>何も入力せず「検索」を押すと全来店記録を表示</span>
            </div>
        </div>""", unsafe_allow_html=True)

    # ────────────────────── 新規来店記録フォーム ──────────────────────────────
    elif mode == "new_record":
        st.markdown("<div class='sec-title'>➕ 新規来店記録</div>", unsafe_allow_html=True)

        with st.form("new_form"):
            # ── 基本情報
            c1, c2, c3 = st.columns(3)
            with c1: f_date    = st.text_input("📅 日付", value=datetime.now().strftime("%Y/%m/%d %H:%M"))
            with c2: f_purpose = st.selectbox("🎯 来店目的", PURPOSE_OPTIONS)
            with c3: f_ctype   = st.selectbox("👤 種別", CUST_TYPE_OPTIONS)

            # ── ナンバープレート
            st.markdown("<div class='sec-title'>ナンバープレート</div>", unsafe_allow_html=True)
            p1, p2, p3, p4 = st.columns([2, 1, 1, 1])
            with p1: f_area   = st.selectbox("地名", PLATE_AREAS)
            with p2: f_3digit = st.text_input("3桁番号", placeholder="500", max_chars=3)
            with p3: f_kana   = st.selectbox("かな", KANA_OPTIONS)
            with p4: f_num    = st.text_input("下4桁", placeholder="1234", max_chars=4)

            # ── 車両情報
            st.markdown("<div class='sec-title'>車両情報</div>", unsafe_allow_html=True)
            v1, v2, v3, v4, v5 = st.columns([2, 2, 2, 1, 1])
            with v1: f_maker  = st.selectbox("メーカー", MAKER_OPTIONS)
            with v2: f_car    = st.text_input("車種", placeholder="プリウス")
            with v3: f_color  = st.selectbox("カラー", COLOR_OPTIONS)
            with v4: f_age    = st.selectbox("年齢", AGE_OPTIONS)
            with v5: f_gender = st.selectbox("性別", GENDER_OPTIONS)

            # ── タイヤ情報
            st.markdown("<div class='sec-title'>タイヤ情報</div>", unsafe_allow_html=True)
            t1, t2, t3, t4 = st.columns([2, 1, 2, 2])
            with t1: f_tsize  = st.text_input("タイヤサイズ", placeholder="225/50R17")
            with t2: f_tyear  = st.text_input("製造年(下2桁)", placeholder="23", max_chars=2)
            with t3: f_tmaker = st.selectbox("タイヤメーカー", TIRE_MAKER_OPTIONS)
            with t4: f_tprod  = st.text_input("タイヤ商品名", placeholder="ENASAVE EC204")

            f_memo = st.text_area("📝 備考", placeholder="接客メモ・特記事項など", height=80)

            sa, sb = st.columns(2)
            with sa: ok = st.form_submit_button("💾 保存する", type="primary", use_container_width=True)
            with sb: ng = st.form_submit_button("キャンセル", use_container_width=True)

        if ok:
            row = {
                "date": f_date, "purpose": f_purpose, "cust_type": f_ctype,
                "plate_area": opt(f_area), "plate_3digit": f_3digit,
                "plate_kana": opt(f_kana), "plate_num": f_num,
                "maker": opt(f_maker), "car_model": f_car, "color": opt(f_color),
                "age": opt(f_age), "gender": f_gender,
                "tire_size": f_tsize, "tire_size_num": tire_to_num(f_tsize),
                "tire_year": f_tyear, "tire_maker": opt(f_tmaker),
                "tire_product": f_tprod, "memo": f_memo,
            }
            updated = pd.concat([pd.DataFrame([row]), load_history()], ignore_index=True)
            save_history(updated)
            st.success("保存しました！")
            st.session_state.mode = "list"
            st.session_state.searched_plate = ""
            st.rerun()

        if ng:
            st.session_state.mode = "list"
            st.rerun()

    # ────────────────────── 一覧（全件 or 絞り込み）─────────────────────────
    elif mode == "list":
        df = load_history()

        if pq:
            filtered = df[df["plate_num"] == pq].copy()
            header   = f"🔎 車番「{pq}」の記録"
        else:
            filtered = df.copy()
            header   = "📋 全来店記録（最新順）"

        filtered["_dt"] = pd.to_datetime(filtered["date"], errors="coerce")
        filtered = filtered.sort_values("_dt", ascending=False).reset_index(drop=True)

        h1, h2 = st.columns([3, 1])
        with h1:
            st.markdown(
                f"<div style='font-size:1rem;font-weight:700;color:#1a1a2e'>{header}"
                f" <span style='font-size:.8rem;color:#aaa;font-weight:400'>({len(filtered)}件)</span></div>",
                unsafe_allow_html=True)
        with h2:
            if st.button("➕ 新規記録", use_container_width=True, key="new2"):
                st.session_state.mode = "new_record"
                st.rerun()

        if filtered.empty:
            st.markdown(
                "<div style='padding:40px;text-align:center;color:#ccc;"
                "border:1px dashed #e0e0e0;border-radius:14px;margin-top:12px'>"
                "記録が見つかりません</div>",
                unsafe_allow_html=True)
        else:
            def mk_badge(text: str, cls: str) -> str:
                return f'<span class="badge {cls}">{text}</span>' if text else ""

            # テーブルヘッダー行（Streamlit columns で再現）
            hcols = st.columns([1.1, 1.1, 0.8, 1.7, 1.7, 0.9, 1.2, 1.0, 2.0, 0.65])
            labels = ["日付","目的","種別","ナンバー","車両","カラー","タイヤサイズ","客層","備考",""]
            for hc, lb in zip(hcols, labels):
                hc.markdown(
                    f"<div style='font-size:.7rem;font-weight:700;color:#aaa;"
                    f"padding-bottom:6px;border-bottom:2px solid #e8e8e8'>{lb}</div>",
                    unsafe_allow_html=True)

            for i, row in filtered.iterrows():
                plate_str = " ".join(filter(None, [row["plate_area"], row["plate_3digit"],
                                                   row["plate_kana"], row["plate_num"]]))
                car_str   = " ".join(filter(None, [row["maker"], row["car_model"]]))
                date_s    = str(row["date"])[:10] if row["date"] else ""
                age_s     = row["age"] if row["age"] not in ("", "(未選択)") else ""
                gender_b  = mk_badge(row["gender"], f"bg-{row['gender']}")
                purpose_b = mk_badge(row["purpose"], "bp")
                ctype_b   = mk_badge(row["cust_type"], f"bt-{row['cust_type']}")

                rcols = st.columns([1.1, 1.1, 0.8, 1.7, 1.7, 0.9, 1.2, 1.0, 2.0, 0.65])
                rcols[0].markdown(f"<div style='font-size:.78rem;color:#bbb;padding-top:5px'>{date_s}</div>", unsafe_allow_html=True)
                rcols[1].markdown(purpose_b, unsafe_allow_html=True)
                rcols[2].markdown(ctype_b, unsafe_allow_html=True)
                rcols[3].markdown(f"<div style='font-size:.83rem;font-weight:600'>{plate_str}</div>", unsafe_allow_html=True)
                rcols[4].markdown(f"<div style='font-size:.83rem'>{car_str}</div>", unsafe_allow_html=True)
                rcols[5].markdown(f"<div style='font-size:.8rem;color:#888'>{row['color']}</div>", unsafe_allow_html=True)
                rcols[6].markdown(f"<div style='font-size:.8rem;color:#888'>{row['tire_size']}</div>", unsafe_allow_html=True)
                rcols[7].markdown(f"{gender_b} <span style='font-size:.75rem;color:#aaa'>{age_s}</span>", unsafe_allow_html=True)
                rcols[8].markdown(
                    f"<div style='font-size:.76rem;color:#999;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>{row['memo']}</div>",
                    unsafe_allow_html=True)

                if rcols[9].button("詳細", key=f"det_{i}", use_container_width=True):
                    st.session_state.mode = "view_record"
                    st.session_state.view_idx = int(i)
                    st.rerun()

                st.markdown("<div style='border-bottom:1px solid #f2f2f2;margin:0 0 2px 0'></div>", unsafe_allow_html=True)

    # ────────────────────── 詳細表示 ──────────────────────────────────────────
    elif mode == "view_record":
        df = load_history()
        df["_dt"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("_dt", ascending=False).reset_index(drop=True)

        idx = st.session_state.view_idx
        if idx is None or idx >= len(df):
            st.session_state.mode = "list"
            st.rerun()

        row = df.iloc[idx]

        if st.button("← 一覧に戻る", key="back"):
            st.session_state.mode = "list"
            st.rerun()

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        plate_str = " ".join(filter(None, [row["plate_area"], row["plate_3digit"],
                                           row["plate_kana"], row["plate_num"]]))
        car_str   = " ".join(filter(None, [row["maker"], row["car_model"]]))

        def badge(text: str, cls: str) -> str:
            return f'<span class="badge {cls}">{text}</span>' if text else ""

        ctype_b  = badge(row["cust_type"], f"bt-{row['cust_type']}")
        gender_b = badge(row["gender"], f"bg-{row['gender']}")
        purp_b   = badge(row["purpose"], "bp")

        tire_full = " ".join(filter(None, [row["tire_size"], row["tire_maker"], row["tire_product"]]))
        tyear_s   = f"{row['tire_year']}年製" if row["tire_year"] else ""
        age_s     = row["age"] if row["age"] not in ("", "(未選択)") else ""
        memo_html = (
            f'<div class="memo-box">📝 {row["memo"]}</div>'
            if row["memo"] else ""
        )

        st.markdown(f"""
        <div class="detail-card">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
                <span style="font-size:1.35rem;font-weight:800;color:#1a1a2e">{plate_str}</span>
                {ctype_b} {purp_b}
            </div>
            <div class="detail-grid">
                <div><span class="detail-label">日時</span><span class="detail-val">{row['date']}</span></div>
                <div><span class="detail-label">車両</span><span class="detail-val">{car_str}</span></div>
                <div><span class="detail-label">カラー</span><span class="detail-val">{row['color']}</span></div>
                <div><span class="detail-label">客層</span><span class="detail-val">{gender_b} {age_s}</span></div>
                <div><span class="detail-label">タイヤ</span><span class="detail-val">{tire_full}</span></div>
                <div><span class="detail-label">製造年</span><span class="detail-val">{tyear_s}</span></div>
            </div>
            {memo_html}
        </div>
        """, unsafe_allow_html=True)

        # 同一車番の過去記録
        same_plate = df[(df["plate_num"] == row["plate_num"]) & (df.index != idx)]
        if not same_plate.empty:
            st.markdown(
                f"<div class='sec-title'>同一車番の過去記録（{len(same_plate)}件）</div>",
                unsafe_allow_html=True)
            for _, pr in same_plate.iterrows():
                pr_purp = badge(pr["purpose"], "bp")
                pr_car  = " ".join(filter(None, [pr["maker"], pr["car_model"]]))
                st.markdown(f"""
                <div style="padding:11px 16px;border:1px solid #ebebeb;border-left:4px solid #a5b4fc;
                            border-radius:0 12px 12px 0;margin-bottom:8px;background:#fff">
                    <div style="font-size:.76rem;color:#aaa;margin-bottom:4px">{pr['date']}</div>
                    <div style="font-size:.88rem;font-weight:600">{pr_purp} &nbsp;{pr_car}</div>
                    <div style="font-size:.8rem;color:#888;margin-top:3px">{pr['memo']}</div>
                </div>
                """, unsafe_allow_html=True)
