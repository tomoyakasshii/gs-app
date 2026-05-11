import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import re
import uuid
import streamlit.components.v1 as components

BASE_DIR     = Path(__file__).parent
HISTORY_CSV  = BASE_DIR / "history.csv"
SCHEDULE_CSV = BASE_DIR / "schedule.csv"

# ── マスターデータ ─────────────────────────────────────────────────────────────
PURPOSE_OPTIONS   = ["給油","燃料券","洗車","オイル交換","バッテリー交換","タイヤ見積","タイヤ交換","車検見積","車検","その他"]
CUST_TYPE_OPTIONS = ["一般","業者","常連"]
PLATE_AREAS = [
    "(未選択)","札幌","函館","旭川","釧路","帯広","北見","室蘭","苫小牧",
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
MAKER_OPTIONS      = ["(未選択)","トヨタ","レクサス","ホンダ","日産","マツダ","スバル","スズキ","ダイハツ","三菱","メルセデス","BMW","アウディ","VW","ボルボ","ジャガー","ランドローバー","その他"]
COLOR_OPTIONS      = ["(未選択)","ホワイト","パールホワイト","シルバー","ガンメタ","ブラック","グレー","ネイビー","ブルー","レッド","ピンク","グリーン","ゴールド","ブラウン","ベージュ","オレンジ","その他"]
AGE_OPTIONS        = ["(未選択)","10代","20代","30代","40代","50代","60代","70代","80代以上"]
GENDER_OPTIONS     = ["無記名","男","女"]
TIRE_MAKER_OPTIONS = ["(未選択)","ブリヂストン","ヨコハマ","ダンロップ","トーヨー","住友(ファルケン)","ミシュラン","コンチネンタル","ピレリ","グッドイヤー","ハンコック","ネクセン","その他"]
KANA_OPTIONS       = ["(未選択)"] + list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん")

HISTORY_COLS = [
    "date","purpose","cust_type",
    "plate_area","plate_3digit","plate_kana","plate_num",
    "maker","car_model","color",
    "age","gender",
    "tire_size","tire_size_num","tire_year","tire_maker","tire_product",
    "memo",
]
SCHEDULE_COLS = ["id","date","time","title","detail","status","plate_num","cust_type"]

DAYS_JP = ["月","火","水","木","金","土","日"]

# ── CSV I/O ───────────────────────────────────────────────────────────────────
def load_history() -> pd.DataFrame:
    if not HISTORY_CSV.exists():
        pd.DataFrame(columns=HISTORY_COLS).to_csv(HISTORY_CSV, index=False)
        return pd.DataFrame(columns=HISTORY_COLS)
    df = pd.read_csv(HISTORY_CSV, dtype=str).fillna("")
    if "plate" in df.columns and "plate_num" not in df.columns:
        df["plate_num"] = df["plate"]
    if "type" in df.columns and "purpose" not in df.columns:
        df["purpose"] = df["type"].str.replace(r"^[\S]+\s+", "", regex=True)
    if "note" in df.columns and "memo" not in df.columns:
        df["memo"] = df["note"]
    for c in HISTORY_COLS:
        if c not in df.columns: df[c] = ""
    return df[HISTORY_COLS]

def save_history(df: pd.DataFrame):
    df[HISTORY_COLS].to_csv(HISTORY_CSV, index=False)

def append_record(row: dict):
    save_history(pd.concat([pd.DataFrame([row]), load_history()], ignore_index=True))

def load_schedule() -> pd.DataFrame:
    if not SCHEDULE_CSV.exists():
        pd.DataFrame(columns=SCHEDULE_COLS).to_csv(SCHEDULE_CSV, index=False)
        return pd.DataFrame(columns=SCHEDULE_COLS)
    df = pd.read_csv(SCHEDULE_CSV, dtype=str).fillna("")
    for c in SCHEDULE_COLS:
        if c not in df.columns: df[c] = ""
    return df[SCHEDULE_COLS]

def save_schedule(df: pd.DataFrame):
    df[SCHEDULE_COLS].to_csv(SCHEDULE_CSV, index=False)

def tire_to_num(s: str) -> str:
    return re.sub(r"[^\d]", "", s)

def opt(v: str) -> str:
    return "" if v == "(未選択)" else v

def sel_idx(options: list, val: str) -> int:
    return options.index(val) if val in options else 0

# ── 見積HTML生成 ──────────────────────────────────────────────────────────────
def generate_estimate_html(
    plan_label: str,
    tire_maker: str, tire_product: str, tire_size: str,
    unit_price: int, qty: int, labor_unit: int, disp_unit: int,
    plate: str, memo: str
) -> str:
    tire_t    = unit_price * qty
    labor_t   = labor_unit  * qty
    disp_t    = disp_unit   * qty
    subtotal  = tire_t + labor_t + disp_t
    tax_amt   = int(subtotal * 0.10)
    total     = subtotal + tax_amt
    date_str  = datetime.now().strftime("%Y年%m月%d日")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<style>
@page {{ size: A4 portrait; margin: 12mm 14mm; }}
*{{ box-sizing:border-box; margin:0; padding:0; }}
body{{ font-family:'Hiragino Kaku Gothic ProN','Yu Gothic','MS Gothic',sans-serif;
      font-size:10.5pt; color:#1a1a2e; background:#fff; }}
/* 印刷時はボタン非表示 */
@media print {{ .noprint{{ display:none!important; }} }}

/* ヘッダー */
.est-header{{
  background:#1B5E20; color:#fff;
  padding:12px 18px; display:flex; justify-content:space-between; align-items:center;
  border-radius:4px 4px 0 0;
}}
.est-header-title{{ font-size:18pt; font-weight:800; letter-spacing:.05em; }}
.est-header-sub{{ font-size:9pt; opacity:.85; }}
.est-doc-title{{
  font-size:13pt; font-weight:700; color:#1B5E20;
  text-align:center; padding:10px 0 6px; border-bottom:2.5px solid #1B5E20;
  letter-spacing:.15em;
}}
.doc-no{{ font-size:8.5pt; color:#888; text-align:right; margin:4px 0 8px; }}

/* 顧客情報 */
.cust-box{{
  display:grid; grid-template-columns:1fr 1fr 1fr;
  gap:0; border:1.5px solid #1B5E20; border-radius:4px; margin:8px 0;
}}
.cust-cell{{
  padding:7px 10px; border-right:1px solid #1B5E20;
}}
.cust-cell:last-child{{ border-right:none; }}
.cust-label{{ font-size:8pt; color:#555; margin-bottom:3px; }}
.cust-val{{ font-size:11pt; font-weight:700; }}

/* 品目テーブル */
table{{ width:100%; border-collapse:collapse; margin:10px 0; }}
thead tr{{ background:#1B5E20; color:#fff; }}
th{{ padding:7px 10px; text-align:center; font-size:9.5pt; font-weight:700; }}
td{{ padding:7px 10px; border-bottom:1px solid #d0e8d0; font-size:10pt; vertical-align:middle; }}
.td-center{{ text-align:center; }}
.td-right{{ text-align:right; }}
.item-main{{ font-weight:600; }}
.item-sub{{ font-size:8.5pt; color:#666; margin-top:1px; }}
tr.subtotal-row td{{ background:#F1F8E9; border-top:1.5px solid #1B5E20; font-weight:600; }}
tr.tax-row td{{ background:#F1F8E9; }}

/* 合計行 */
tr.total-row td{{
  background:#FCE4EC; border-top:2px solid #C62828;
  font-size:13pt; font-weight:800; color:#C62828;
  padding:10px;
}}
.total-label{{ font-size:10pt; }}

/* プランバッジ */
.plan-badge{{
  display:inline-block; background:#1B5E20; color:#fff;
  padding:3px 14px; border-radius:20px; font-size:9pt; font-weight:700;
  margin-bottom:10px;
}}

/* メモ */
.memo-section{{
  border:1.5px solid #E91E63; border-radius:4px; padding:10px 14px; margin-top:12px;
}}
.memo-title{{ font-size:9pt; font-weight:700; color:#E91E63; margin-bottom:6px; }}
.memo-body{{ font-size:10pt; line-height:1.8; min-height:60px; white-space:pre-wrap; }}

/* フッター */
.footer{{
  margin-top:20px; border-top:1px solid #ccc;
  padding-top:8px; font-size:8.5pt; color:#888;
  display:flex; justify-content:space-between;
}}
.stamp-area{{
  border:1px solid #ccc; border-radius:4px;
  width:80px; height:50px; text-align:center;
  font-size:8pt; color:#ccc; line-height:50px;
}}

/* 印刷ボタン */
.print-btn{{
  display:block; margin:14px auto 8px; padding:10px 36px;
  background:#1B5E20; color:#fff; border:none; border-radius:8px;
  font-size:13pt; font-weight:700; cursor:pointer; letter-spacing:.05em;
}}
.print-btn:hover{{ background:#2E7D32; }}
</style>
</head>
<body>
<button class="print-btn noprint" onclick="window.print()">🖨️ 印刷する</button>

<div class="est-header">
  <div>
    <div class="est-header-title">⛽ タイヤ見積書</div>
    <div class="est-header-sub">GS 接客支援システム</div>
  </div>
  <div style="text-align:right;font-size:9.5pt">
    発行日：{date_str}<br>
    担当：___________
  </div>
</div>

<div class="est-doc-title">タ イ ヤ 御 見 積 書</div>
<div class="doc-no">No. {datetime.now().strftime("%Y%m%d%H%M")}</div>

<div style="margin:4px 0 8px">
  <span class="plan-badge">{'⭐ プランA　オススメ' if plan_label=='A' else '💰 プランB　お買い得'}</span>
</div>

<div class="cust-box">
  <div class="cust-cell">
    <div class="cust-label">車番</div>
    <div class="cust-val">{plate if plate else '　　　　'}</div>
  </div>
  <div class="cust-cell">
    <div class="cust-label">タイヤサイズ</div>
    <div class="cust-val">{tire_size if tire_size else '　　　　'}</div>
  </div>
  <div class="cust-cell">
    <div class="cust-label">発行日</div>
    <div class="cust-val">{date_str}</div>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width:42%;text-align:left">品名・内容</th>
      <th style="width:8%">数量</th>
      <th style="width:12%">単位</th>
      <th style="width:19%">単価（税抜）</th>
      <th style="width:19%">金額（税抜）</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>
        <div class="item-main">タイヤ代　{tire_maker}</div>
        <div class="item-sub">{tire_product}　{tire_size}</div>
      </td>
      <td class="td-center">{qty}</td>
      <td class="td-center">本</td>
      <td class="td-right">¥{unit_price:,}</td>
      <td class="td-right">¥{tire_t:,}</td>
    </tr>
    <tr>
      <td><div class="item-main">タイヤ取付工賃</div></td>
      <td class="td-center">{qty}</td>
      <td class="td-center">本</td>
      <td class="td-right">¥{labor_unit:,}</td>
      <td class="td-right">¥{labor_t:,}</td>
    </tr>
    <tr>
      <td><div class="item-main">廃タイヤ処理料</div></td>
      <td class="td-center">{qty}</td>
      <td class="td-center">本</td>
      <td class="td-right">¥{disp_unit:,}</td>
      <td class="td-right">¥{disp_t:,}</td>
    </tr>
    <tr class="subtotal-row">
      <td colspan="4" style="text-align:right">小 計（税抜）</td>
      <td class="td-right">¥{subtotal:,}</td>
    </tr>
    <tr class="tax-row">
      <td colspan="4" style="text-align:right">消費税（10%）</td>
      <td class="td-right">¥{tax_amt:,}</td>
    </tr>
    <tr class="total-row">
      <td colspan="4" style="text-align:right">
        <span class="total-label">★ 合 計（税込）</span>
      </td>
      <td class="td-right">¥{total:,}</td>
    </tr>
  </tbody>
</table>

<div class="memo-section">
  <div class="memo-title">📝 接客メモ・特記事項</div>
  <div class="memo-body">{memo if memo else '　'}</div>
</div>

<div class="footer">
  <div>
    ※ 本見積の有効期限は発行日より30日間です。<br>
    ※ 価格はすべて消費税10%込みの金額です。
  </div>
  <div style="text-align:right">
    <div class="stamp-area">確認印</div>
  </div>
</div>

</body>
</html>"""


# ── ページ設定 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GS接客支援システム",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

defaults = {
    "digits": "",
    "searched_plate": None,
    "mode": "list",
    # "list"|"new_record"|"edit_record"|"view_record"|"quote"|"schedule"
    "view_idx": None,    # original CSV index for view/edit
    "edit_idx": None,
    "week_offset": 0,    # schedule: 0=今週, ±N週
    "show_sched_form": False,
    "print_plan": "A",
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

/* テンキー */
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(3):last-child) [data-testid="column"]{width:31%!important;flex:1 1 31%!important;min-width:31%!important;}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(3):last-child) [data-testid="stButton"]>button{height:64px!important;font-size:1.35rem!important;font-weight:700!important;background:#f7f7f7!important;border:1.5px solid #e3e3e3!important;border-radius:14px!important;color:#1a1a2e!important;box-shadow:0 1px 4px rgba(0,0,0,.06)!important;padding:0!important;transition:background .08s,transform .08s!important;}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(3):last-child) [data-testid="stButton"]>button:hover{background:#ebebeb!important;}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(3):last-child) [data-testid="stButton"]>button:active{background:#d8d8d8!important;transform:scale(.94)!important;}

/* Primary */
[data-testid="stButton"]>button[data-testid="baseButton-primary"]{background:#2563eb!important;border-color:#1d4ed8!important;color:#fff!important;font-weight:700!important;height:48px!important;border-radius:12px!important;}
[data-testid="stButton"]>button[data-testid="baseButton-primary"]:hover{background:#1d4ed8!important;box-shadow:0 4px 14px rgba(37,99,235,.3)!important;}

/* ディスプレイ */
.numpad-display{background:linear-gradient(135deg,#f9f9f9,#efefef);border:1.5px solid #e0e0e0;border-radius:16px;height:64px;display:flex;align-items:center;justify-content:center;margin-bottom:10px;}
.d-val{font-size:2.1rem;font-weight:800;letter-spacing:.5rem;color:#1a1a2e;font-variant-numeric:tabular-nums;}
.d-ph{font-size:1rem;color:#c8c8c8;letter-spacing:.4rem;}

/* フィールド */
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stNumberInput"] input{background:#fff!important;border:1.5px solid #e8e8e8!important;border-radius:10px!important;font-size:.92rem!important;color:#1a1a2e!important;transition:border-color .15s!important;}
[data-testid="stTextInput"] input:focus,[data-testid="stTextArea"] textarea:focus{border-color:#2563eb!important;box-shadow:0 0 0 3px rgba(37,99,235,.12)!important;}
[data-testid="stSelectbox"]>div>div{border:1.5px solid #e8e8e8!important;border-radius:10px!important;}

/* バッジ */
.badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:.73rem;font-weight:600;}
.bp{background:#e0f2fe;color:#0369a1;}
.bt-一般{background:#f1f5f9;color:#64748b;}
.bt-業者{background:#fef3c7;color:#92400e;}
.bt-常連{background:#d1fae5;color:#065f46;}
.bg-男{background:#dbeafe;color:#1d4ed8;}
.bg-女{background:#fce7f3;color:#9d174d;}
.bg-無記名{background:#f1f5f9;color:#94a3b8;}

/* 見積カード */
.q-card{border-radius:16px;padding:14px 16px;margin-bottom:4px;}
.q-card-a{background:linear-gradient(135deg,#eff6ff,#dbeafe);border:1.5px solid #93c5fd;}
.q-card-b{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:1.5px solid #86efac;}
.q-row{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,.06);font-size:.84rem;}
.q-row:last-child{border-bottom:none;}
.q-label{color:#666;}
.q-val{font-weight:600;color:#1a1a2e;}
.q-total-a{font-size:1.25rem;font-weight:800;color:#1d4ed8;padding-top:10px;margin-top:6px;border-top:2px solid #93c5fd;display:flex;justify-content:space-between;}
.q-total-b{font-size:1.25rem;font-weight:800;color:#15803d;padding-top:10px;margin-top:6px;border-top:2px solid #86efac;display:flex;justify-content:space-between;}
.q-plan-a{font-size:.92rem;font-weight:800;color:#1d4ed8;margin-bottom:8px;}
.q-plan-b{font-size:.92rem;font-weight:800;color:#15803d;margin-bottom:8px;}

/* A表チェック */
.acheck-ok{background:#f0fdf4;border:1px solid #86efac;border-radius:12px;padding:10px 12px;text-align:center;}
.acheck-ng{background:#fef2f2;border:1px solid #fca5a5;border-radius:12px;padding:10px 12px;text-align:center;}

/* 予定ボード */
.sched-col-header{text-align:center;font-weight:700;font-size:.82rem;padding:6px 0;border-radius:8px 8px 0 0;margin-bottom:4px;}
.sched-col-today{background:#2563eb;color:#fff;}
.sched-col-normal{background:#f1f5f9;color:#555;}
.sched-col-past{background:#f8f8f8;color:#bbb;}
.sched-item{background:#fffde7;border:1.5px solid #f9d71c;border-left:4px solid #f59e0b;border-radius:8px;padding:8px 10px;margin-bottom:6px;font-size:.8rem;}
.sched-item-done{background:#f1f5f9;border:1.5px solid #e2e8f0;border-left:4px solid #94a3b8;border-radius:8px;padding:8px 10px;margin-bottom:6px;font-size:.8rem;opacity:.65;}
.sched-pin{font-size:.95rem;margin-right:4px;}
.sched-title{font-weight:700;color:#1a1a2e;margin-bottom:2px;}
.sched-detail{color:#666;font-size:.76rem;}

/* 詳細カード */
.detail-card{background:#fafafa;border:1px solid #ebebeb;border-radius:16px;padding:20px 22px;margin-bottom:12px;}
.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 28px;font-size:.88rem;margin-top:12px;}
.detail-label{color:#aaa;font-size:.74rem;display:block;margin-bottom:2px;}
.detail-val{color:#1a1a2e;font-weight:500;}
.memo-box{margin-top:14px;padding:10px 14px;background:#fff9ee;border-left:4px solid #f0a500;border-radius:0 8px 8px 0;font-size:.86rem;color:#6b4c00;line-height:1.75;}

.divider{border:none;border-top:1px solid #f0f0f0;margin:10px 0;}
.sec-title{font-size:.72rem;font-weight:700;color:#aaa;letter-spacing:.08em;text-transform:uppercase;margin:14px 0 5px;}
</style>
""", unsafe_allow_html=True)

# ── タイトル ──────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='font-size:1.4rem;font-weight:800;color:#1a1a2e;margin-bottom:0'>⛽ GS 接客支援システム</h1>",
    unsafe_allow_html=True)
st.markdown("<hr class='divider'>", unsafe_allow_html=True)

left, right = st.columns([1, 2.4], gap="large")

# ═══════════════════════════════════════════════════════════════════════════════
#  LEFT ── テンキー
# ═══════════════════════════════════════════════════════════════════════════════
with left:
    st.markdown("<p style='font-size:.86rem;font-weight:700;color:#555;margin:0 0 8px 0'>🔢 車番下4桁で検索</p>", unsafe_allow_html=True)
    _slot = st.empty()

    KEYS = [("7","n7"),("8","n8"),("9","n9"),
            ("4","n4"),("5","n5"),("6","n6"),
            ("1","n1"),("2","n2"),("3","n3"),
            ("C","nc"),("⌫","nd"),("0","n0")]
    for i in range(0, 12, 3):
        c3 = st.columns(3)
        for col, (label, key) in zip(c3, KEYS[i:i+3]):
            with col:
                if st.button(label, key=key, use_container_width=True):
                    if label == "C":   st.session_state.digits = ""
                    elif label == "⌫": st.session_state.digits = st.session_state.digits[:-1]
                    elif label.isdigit() and len(st.session_state.digits) < 4:
                        st.session_state.digits += label
                    if len(st.session_state.digits) == 4:
                        st.session_state.searched_plate = st.session_state.digits
                        st.session_state.digits = ""
                        st.session_state.mode = "list"
                        st.session_state.view_idx = None

    if st.button("🔍  検索", key="nsearch", type="primary", use_container_width=True):
        st.session_state.searched_plate = st.session_state.digits
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
        st.session_state.mode = "new_record"; st.session_state.view_idx = None
    if st.button("🛞 タイヤ見積作成", use_container_width=True, key="btn_quote"):
        st.session_state.mode = "quote";      st.session_state.view_idx = None
    if st.button("📅 予定ボード", use_container_width=True, key="btn_sched"):
        st.session_state.mode = "schedule";   st.session_state.view_idx = None

# ═══════════════════════════════════════════════════════════════════════════════
#  RIGHT
# ═══════════════════════════════════════════════════════════════════════════════
with right:
    pq   = st.session_state.searched_plate
    mode = st.session_state.mode

    # ── 初期画面 ──────────────────────────────────────────────────────────────
    if pq is None and mode not in ("new_record","edit_record","view_record","quote","schedule"):
        st.markdown("""<div style="padding:60px 32px;text-align:center;">
            <div style="font-size:3rem;margin-bottom:14px">🔍</div>
            <div style="font-size:.9rem;color:#bbb;line-height:2.4">
                左のテンキーで車番下4桁を入力<br>
                <span style='color:#ccc;font-size:.78rem'>空のまま「検索」→ 全記録を表示</span>
            </div></div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════════
    #  🛞 見積作成
    # ════════════════════════════════════════════════════════════════════════════
    elif mode == "quote":
        if st.button("← 戻る", key="quote_back"):
            st.session_state.mode = "list"; st.rerun()

        st.markdown("<div style='font-size:1rem;font-weight:800;color:#1a1a2e;margin:6px 0 2px'>🛞 タイヤ見積作成</div>", unsafe_allow_html=True)

        # 共通設定
        st.markdown("<div class='sec-title'>共通設定</div>", unsafe_allow_html=True)
        s1,s2,s3,s4 = st.columns(4)
        with s1: q_qty        = st.selectbox("本数", [4,2,1], key="q_qty")
        with s2: q_labor_unit = st.number_input("工賃（1本・税抜）", min_value=0, value=2500, step=100, key="q_labor_unit", format="%d")
        with s3: q_disp_unit  = st.number_input("廃タイヤ（1本）",   min_value=0, value=300,  step=50,  key="q_disp_unit",  format="%d")
        with s4: q_plate      = st.text_input("車番下4桁（任意）", placeholder="1234", max_chars=4, key="q_plate")

        labor_sub = q_labor_unit * q_qty
        disp_sub  = q_disp_unit  * q_qty

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # プランA / B 並列入力
        col_a, col_b = st.columns(2, gap="medium")
        plans: dict = {}
        for col, pk, card_cls, total_cls, plan_lbl_cls, emoji, pname in [
            (col_a,"A","q-card-a","q-total-a","q-plan-a","⭐","プランA　オススメ"),
            (col_b,"B","q-card-b","q-total-b","q-plan-b","💰","プランB　お買い得"),
        ]:
            with col:
                st.markdown(f"<div class='{card_cls} q-card'>", unsafe_allow_html=True)
                st.markdown(f"<div class='{plan_lbl_cls}'>{emoji} {pname}</div>", unsafe_allow_html=True)
                tm   = st.selectbox("タイヤメーカー", TIRE_MAKER_OPTIONS, key=f"q_{pk}_tm")
                tp   = st.text_input("商品名", placeholder="ENASAVE EC204", key=f"q_{pk}_tp")
                ts   = st.text_input("タイヤサイズ", placeholder="195/65R15", key=f"q_{pk}_ts")
                unit = st.number_input("単価（1本・税抜）", min_value=0, value=15000, step=500, key=f"q_{pk}_price", format="%d")
                tire_t   = unit * q_qty
                subtotal = tire_t + labor_sub + disp_sub
                tax_amt  = int(subtotal * 0.10)
                total    = subtotal + tax_amt
                plans[pk] = {"maker":opt(tm),"product":tp,"size":ts,"unit":unit,
                              "tire_t":tire_t,"subtotal":subtotal,"tax":tax_amt,"total":total}
                st.markdown(f"""
                <div style="margin-top:10px">
                <div class="q-row"><span class="q-label">🛞 タイヤ代（{q_qty}本）</span><span class="q-val">¥{tire_t:,}</span></div>
                <div class="q-row"><span class="q-label">🔧 工賃（{q_qty}本）</span><span class="q-val">¥{labor_sub:,}</span></div>
                <div class="q-row"><span class="q-label">♻️ 廃タイヤ（{q_qty}本）</span><span class="q-val">¥{disp_sub:,}</span></div>
                <div class="q-row"><span class="q-label">消費税（10%）</span><span class="q-val">¥{tax_amt:,}</span></div>
                <div class="{total_cls}"><span>税込合計</span><span>¥{total:,}</span></div>
                </div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        # A表チェック
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown("<div class='sec-title'>📊 A表（3割引ライン）チェック</div>", unsafe_allow_html=True)
        ac1, ac2 = st.columns([1,2])
        with ac1:
            a_unit = st.number_input("A表単価（1本・税抜）", min_value=0, value=20000, step=500, key="a_unit", format="%d")
        a_tire_line  = int(a_unit * q_qty * 0.70)
        a_total_line = a_tire_line + labor_sub + disp_sub
        with ac2:
            st.markdown(f"""
            <div style="background:#f8faff;border:1px solid #dbeafe;border-radius:12px;padding:10px 14px;margin-top:22px">
                <div style="font-size:.73rem;color:#4b6cb7;font-weight:700;margin-bottom:5px">A表3割引ライン（税抜・全込み）</div>
                <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:.82rem">
                    <span>タイヤ: <b>¥{a_tire_line:,}</b></span>
                    <span>工賃: <b>¥{labor_sub:,}</b></span>
                    <span>廃タイヤ: <b>¥{disp_sub:,}</b></span>
                    <span style="font-size:.98rem;font-weight:800;color:#1d4ed8">最低ライン ¥{a_total_line:,}</span>
                </div>
            </div>""", unsafe_allow_html=True)

        chk_a, chk_b = st.columns(2)
        for cc, pk, pname in [(chk_a,"A","プランA"),(chk_b,"B","プランB")]:
            diff = plans[pk]["subtotal"] - a_total_line
            ok   = diff >= 0
            with cc:
                if ok:
                    st.markdown(f'<div class="acheck-ok"><div style="font-size:1.3rem">✅</div><div style="font-weight:700;color:#166534">{pname}　利益あり</div><div style="font-size:.8rem;color:#166534">+¥{diff:,}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="acheck-ng"><div style="font-size:1.3rem">❌</div><div style="font-weight:700;color:#991b1b">{pname}　赤字注意</div><div style="font-size:.8rem;color:#991b1b">-¥{abs(diff):,} 不足</div></div>', unsafe_allow_html=True)

        # 接客メモ
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown("<div class='sec-title'>✏️ 接客メモ（殴り書きOK）</div>", unsafe_allow_html=True)
        st.markdown("<div style='background:#fffde7;border:1.5px solid #f9d71c;border-radius:10px;padding:4px 8px'>", unsafe_allow_html=True)
        q_memo = st.text_area("接客メモ", placeholder="お客様要望・タイヤ状態・次回案内など", height=150, key="q_memo", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── 印刷プレビュー ────────────────────────────────────────────────────
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown("<div class='sec-title'>🖨️ 見積書印刷</div>", unsafe_allow_html=True)
        pr1, pr2, pr3, pr4 = st.columns(4)
        with pr1:
            print_plan = st.radio("印刷するプラン", ["A（オススメ）","B（お買い得）"], horizontal=True, key="print_plan_sel")
        with pr2:
            do_print = st.button("📄 見積書プレビュー・印刷", use_container_width=True, key="do_print")

        if do_print or st.session_state.get("show_print"):
            st.session_state["show_print"] = True
            sel = "A" if "A" in print_plan else "B"
            p   = plans[sel]
            html_str = generate_estimate_html(
                sel, p["maker"], p["product"], p["size"],
                p["unit"], q_qty, q_labor_unit, q_disp_unit,
                q_plate, q_memo
            )
            components.html(html_str, height=980, scrolling=True)
            if st.button("プレビューを閉じる", key="close_print"):
                st.session_state["show_print"] = False
                st.rerun()
        else:
            st.session_state["show_print"] = False

        # 保存ボタン
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        sv_a, sv_b, sv_c = st.columns(3)

        def build_quote_row(pk: str) -> dict:
            p = plans[pk]
            note = (f"【プラン{pk}】{p['maker']} {p['product']} {p['size']} "
                    f"/ {q_qty}本 / ¥{p['unit']:,}/本 / 税込¥{p['total']:,}"
                    + (f"\n{q_memo}" if q_memo else ""))
            return {"date":datetime.now().strftime("%Y/%m/%d %H:%M"),"purpose":"タイヤ見積",
                    "cust_type":"","plate_area":"","plate_3digit":"","plate_kana":"",
                    "plate_num":q_plate,"maker":"","car_model":"","color":"","age":"","gender":"",
                    "tire_size":p["size"],"tire_size_num":tire_to_num(p["size"]),
                    "tire_year":"","tire_maker":p["maker"],"tire_product":p["product"],"memo":note}

        with sv_a:
            if st.button("📋 プランAで保存", type="primary", use_container_width=True, key="save_qa"):
                append_record(build_quote_row("A"))
                st.success("プランA保存完了！"); st.session_state.mode="list"; st.session_state.searched_plate=q_plate or ""; st.rerun()
        with sv_b:
            if st.button("📋 プランBで保存", use_container_width=True, key="save_qb"):
                append_record(build_quote_row("B"))
                st.success("プランB保存完了！"); st.session_state.mode="list"; st.session_state.searched_plate=q_plate or ""; st.rerun()
        with sv_c:
            if st.button("閉じる", use_container_width=True, key="close_quote"):
                st.session_state.mode="list"; st.rerun()

    # ════════════════════════════════════════════════════════════════════════════
    #  📅 予定ボード
    # ════════════════════════════════════════════════════════════════════════════
    elif mode == "schedule":
        # 週計算
        today     = datetime.now().date()
        week_off  = st.session_state.week_offset
        monday    = today - timedelta(days=today.weekday()) + timedelta(weeks=week_off)
        week_days = [monday + timedelta(days=d) for d in range(7)]
        sched_df  = load_schedule()

        # ヘッダー
        hc1, hc2, hc3, hc4, hc5 = st.columns([2, 0.7, 0.7, 1.5, 1.5])
        with hc1:
            st.markdown(f"<div style='font-size:.98rem;font-weight:800;color:#1a1a2e'>"
                        f"📅 予定ボード　<span style='font-size:.78rem;color:#aaa;font-weight:400'>"
                        f"{monday.strftime('%Y/%m/%d')} 週</span></div>", unsafe_allow_html=True)
        with hc2:
            if st.button("◀ 前週", use_container_width=True, key="week_prev"):
                st.session_state.week_offset -= 1; st.rerun()
        with hc3:
            if st.button("次週 ▶", use_container_width=True, key="week_next"):
                st.session_state.week_offset += 1; st.rerun()
        with hc4:
            if st.button("今週に戻る", use_container_width=True, key="week_reset"):
                st.session_state.week_offset = 0; st.rerun()
        with hc5:
            if st.button("➕ 予定を追加", use_container_width=True, key="sched_add"):
                st.session_state.show_sched_form = not st.session_state.get("show_sched_form", False)

        # 予定追加フォーム
        if st.session_state.get("show_sched_form"):
            with st.form("sched_form"):
                sf1, sf2, sf3 = st.columns(3)
                with sf1: sf_date    = st.text_input("日付", value=today.strftime("%Y/%m/%d"))
                with sf2: sf_time    = st.text_input("時間", value="10:00", placeholder="10:30")
                with sf3: sf_plate   = st.text_input("車番（任意）", placeholder="1234", max_chars=4)
                sf4, sf5 = st.columns(2)
                with sf4: sf_title   = st.text_input("タイトル", placeholder="タイヤ交換")
                with sf5: sf_ctype   = st.selectbox("種別", CUST_TYPE_OPTIONS)
                sf_detail = st.text_area("詳細メモ", placeholder="お客様の要望など", height=70)
                ok_s, ng_s = st.columns(2)
                with ok_s: sf_ok = st.form_submit_button("💾 追加", type="primary", use_container_width=True)
                with ng_s: sf_ng = st.form_submit_button("キャンセル", use_container_width=True)
            if sf_ok:
                new_s = {"id":str(uuid.uuid4()),"date":sf_date,"time":sf_time,
                         "title":sf_title,"detail":sf_detail,"status":"予定",
                         "plate_num":sf_plate,"cust_type":sf_ctype}
                save_schedule(pd.concat([sched_df, pd.DataFrame([new_s])], ignore_index=True))
                st.session_state.show_sched_form = False; st.rerun()
            if sf_ng:
                st.session_state.show_sched_form = False; st.rerun()

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # 7列カレンダーグリッド
        day_cols = st.columns(7, gap="small")
        for dc, day in zip(day_cols, week_days):
            is_today = (day == today)
            is_past  = (day < today)
            dow_jp   = DAYS_JP[day.weekday()]
            hdr_cls  = "sched-col-today" if is_today else ("sched-col-past" if is_past else "sched-col-normal")
            day_str  = day.strftime("%Y/%m/%d")
            day_items = sched_df[sched_df["date"] == day_str] if not sched_df.empty else pd.DataFrame()

            with dc:
                st.markdown(
                    f"<div class='sched-col-header {hdr_cls}'>{dow_jp}<br>"
                    f"<span style='font-size:.75rem'>{day.strftime('%m/%d')}</span></div>",
                    unsafe_allow_html=True)

                if day_items.empty:
                    st.markdown("<div style='font-size:.7rem;color:#ddd;text-align:center;padding:6px 0'>─</div>", unsafe_allow_html=True)
                else:
                    for _, si in day_items.iterrows():
                        done = si["status"] == "完了"
                        item_cls = "sched-item-done" if done else "sched-item"
                        plate_s  = f"#{si['plate_num']}" if si["plate_num"] else ""
                        st.markdown(
                            f"<div class='{item_cls}'>"
                            f"<div class='sched-title'><span class='sched-pin'>📌</span>{si['time']} {si['title']}</div>"
                            f"<div class='sched-detail'>{plate_s} {si['detail'][:20]}</div>"
                            f"</div>",
                            unsafe_allow_html=True)
                        if not done:
                            if st.button("✅ 完了", key=f"done_{si['id']}", use_container_width=True):
                                sched_df.loc[sched_df["id"]==si["id"], "status"] = "完了"
                                save_schedule(sched_df)
                                # 履歴にも書き込み
                                append_record({
                                    "date": f"{si['date']} {si['time']}",
                                    "purpose": si["title"], "cust_type": si["cust_type"],
                                    "plate_area":"","plate_3digit":"","plate_kana":"",
                                    "plate_num": si["plate_num"],
                                    "maker":"","car_model":"","color":"","age":"","gender":"",
                                    "tire_size":"","tire_size_num":"","tire_year":"",
                                    "tire_maker":"","tire_product":"",
                                    "memo": f"【予定完了】{si['detail']}",
                                })
                                st.rerun()

    # ════════════════════════════════════════════════════════════════════════════
    #  ➕ 新規来店記録
    # ════════════════════════════════════════════════════════════════════════════
    elif mode == "new_record":
        st.markdown("<div class='sec-title'>➕ 新規来店記録</div>", unsafe_allow_html=True)
        with st.form("new_form"):
            c1,c2,c3 = st.columns(3)
            with c1: f_date    = st.text_input("📅 日付", value=datetime.now().strftime("%Y/%m/%d %H:%M"))
            with c2: f_purpose = st.selectbox("🎯 来店目的", PURPOSE_OPTIONS)
            with c3: f_ctype   = st.selectbox("👤 種別", CUST_TYPE_OPTIONS)
            st.markdown("<div class='sec-title'>ナンバープレート</div>", unsafe_allow_html=True)
            p1,p2,p3,p4 = st.columns([2,1,1,1])
            with p1: f_area   = st.selectbox("地名", PLATE_AREAS)
            with p2: f_3digit = st.text_input("3桁", placeholder="500", max_chars=3)
            with p3: f_kana   = st.selectbox("かな", KANA_OPTIONS)
            with p4: f_num    = st.text_input("下4桁", placeholder="1234", max_chars=4)
            st.markdown("<div class='sec-title'>車両情報</div>", unsafe_allow_html=True)
            v1,v2,v3,v4,v5 = st.columns([2,2,2,1,1])
            with v1: f_maker  = st.selectbox("メーカー", MAKER_OPTIONS)
            with v2: f_car    = st.text_input("車種", placeholder="プリウス")
            with v3: f_color  = st.selectbox("カラー", COLOR_OPTIONS)
            with v4: f_age    = st.selectbox("年齢", AGE_OPTIONS)
            with v5: f_gender = st.selectbox("性別", GENDER_OPTIONS)
            st.markdown("<div class='sec-title'>タイヤ情報</div>", unsafe_allow_html=True)
            t1,t2,t3,t4 = st.columns([2,1,2,2])
            with t1: f_tsize  = st.text_input("タイヤサイズ", placeholder="225/50R17")
            with t2: f_tyear  = st.text_input("製造年(下2桁)", placeholder="23", max_chars=2)
            with t3: f_tmaker = st.selectbox("タイヤメーカー", TIRE_MAKER_OPTIONS)
            with t4: f_tprod  = st.text_input("タイヤ商品名", placeholder="ENASAVE EC204")
            f_memo = st.text_area("📝 備考", placeholder="接客メモ・特記事項など", height=80)
            sa,sb = st.columns(2)
            with sa: ok = st.form_submit_button("💾 保存する", type="primary", use_container_width=True)
            with sb: ng = st.form_submit_button("キャンセル", use_container_width=True)
        if ok:
            append_record({"date":f_date,"purpose":f_purpose,"cust_type":f_ctype,
                           "plate_area":opt(f_area),"plate_3digit":f_3digit,
                           "plate_kana":opt(f_kana),"plate_num":f_num,
                           "maker":opt(f_maker),"car_model":f_car,"color":opt(f_color),
                           "age":opt(f_age),"gender":f_gender,
                           "tire_size":f_tsize,"tire_size_num":tire_to_num(f_tsize),
                           "tire_year":f_tyear,"tire_maker":opt(f_tmaker),
                           "tire_product":f_tprod,"memo":f_memo})
            st.success("保存しました！"); st.session_state.mode="list"; st.session_state.searched_plate=""; st.rerun()
        if ng:
            st.session_state.mode="list"; st.rerun()

    # ════════════════════════════════════════════════════════════════════════════
    #  ✏️ 履歴編集（全16項目）
    # ════════════════════════════════════════════════════════════════════════════
    elif mode == "edit_record":
        df  = load_history()
        idx = st.session_state.edit_idx
        if idx is None or idx not in df.index:
            st.session_state.mode = "list"; st.rerun()

        row = df.loc[idx]
        if st.button("← 一覧に戻る（変更を破棄）", key="edit_back"):
            st.session_state.mode = "list"; st.rerun()

        st.markdown(f"<div style='font-size:.98rem;font-weight:800;color:#1a1a2e;margin:8px 0 4px'>✏️ 来店記録を編集</div>", unsafe_allow_html=True)

        with st.form("edit_form"):
            c1,c2,c3 = st.columns(3)
            with c1: f_date    = st.text_input("📅 日付", value=row["date"])
            with c2: f_purpose = st.selectbox("🎯 来店目的", PURPOSE_OPTIONS, index=sel_idx(PURPOSE_OPTIONS, row["purpose"]))
            with c3: f_ctype   = st.selectbox("👤 種別", CUST_TYPE_OPTIONS, index=sel_idx(CUST_TYPE_OPTIONS, row["cust_type"]))
            st.markdown("<div class='sec-title'>ナンバープレート</div>", unsafe_allow_html=True)
            p1,p2,p3,p4 = st.columns([2,1,1,1])
            with p1: f_area   = st.selectbox("地名", PLATE_AREAS, index=sel_idx(PLATE_AREAS, row["plate_area"] or "(未選択)"))
            with p2: f_3digit = st.text_input("3桁", value=row["plate_3digit"], max_chars=3)
            with p3: f_kana   = st.selectbox("かな", KANA_OPTIONS, index=sel_idx(KANA_OPTIONS, row["plate_kana"] or "(未選択)"))
            with p4: f_num    = st.text_input("下4桁", value=row["plate_num"], max_chars=4)
            st.markdown("<div class='sec-title'>車両情報</div>", unsafe_allow_html=True)
            v1,v2,v3,v4,v5 = st.columns([2,2,2,1,1])
            with v1: f_maker  = st.selectbox("メーカー", MAKER_OPTIONS, index=sel_idx(MAKER_OPTIONS, row["maker"] or "(未選択)"))
            with v2: f_car    = st.text_input("車種", value=row["car_model"])
            with v3: f_color  = st.selectbox("カラー", COLOR_OPTIONS, index=sel_idx(COLOR_OPTIONS, row["color"] or "(未選択)"))
            with v4: f_age    = st.selectbox("年齢", AGE_OPTIONS, index=sel_idx(AGE_OPTIONS, row["age"] or "(未選択)"))
            with v5: f_gender = st.selectbox("性別", GENDER_OPTIONS, index=sel_idx(GENDER_OPTIONS, row["gender"]))
            st.markdown("<div class='sec-title'>タイヤ情報</div>", unsafe_allow_html=True)
            t1,t2,t3,t4 = st.columns([2,1,2,2])
            with t1: f_tsize  = st.text_input("タイヤサイズ", value=row["tire_size"])
            with t2: f_tyear  = st.text_input("製造年(下2桁)", value=row["tire_year"], max_chars=2)
            with t3: f_tmaker = st.selectbox("タイヤメーカー", TIRE_MAKER_OPTIONS, index=sel_idx(TIRE_MAKER_OPTIONS, row["tire_maker"] or "(未選択)"))
            with t4: f_tprod  = st.text_input("タイヤ商品名", value=row["tire_product"])
            f_memo = st.text_area("📝 備考", value=row["memo"], height=90)
            sa,sb = st.columns(2)
            with sa: ok = st.form_submit_button("💾 上書き保存", type="primary", use_container_width=True)
            with sb: ng = st.form_submit_button("キャンセル", use_container_width=True)

        if ok:
            df.loc[idx, "date"]         = f_date
            df.loc[idx, "purpose"]      = f_purpose
            df.loc[idx, "cust_type"]    = f_ctype
            df.loc[idx, "plate_area"]   = opt(f_area)
            df.loc[idx, "plate_3digit"] = f_3digit
            df.loc[idx, "plate_kana"]   = opt(f_kana)
            df.loc[idx, "plate_num"]    = f_num
            df.loc[idx, "maker"]        = opt(f_maker)
            df.loc[idx, "car_model"]    = f_car
            df.loc[idx, "color"]        = opt(f_color)
            df.loc[idx, "age"]          = opt(f_age)
            df.loc[idx, "gender"]       = f_gender
            df.loc[idx, "tire_size"]    = f_tsize
            df.loc[idx, "tire_size_num"]= tire_to_num(f_tsize)
            df.loc[idx, "tire_year"]    = f_tyear
            df.loc[idx, "tire_maker"]   = opt(f_tmaker)
            df.loc[idx, "tire_product"] = f_tprod
            df.loc[idx, "memo"]         = f_memo
            save_history(df)
            st.success("更新しました！"); st.session_state.mode="list"; st.rerun()
        if ng:
            st.session_state.mode="list"; st.rerun()

    # ════════════════════════════════════════════════════════════════════════════
    #  📋 一覧（全件 or 絞り込み）
    # ════════════════════════════════════════════════════════════════════════════
    elif mode == "list":
        df = load_history()
        if pq:
            filtered = df[df["plate_num"] == pq].copy()
            header   = f"🔎 車番「{pq}」の記録"
        else:
            filtered = df.copy()
            header   = "📋 全来店記録（最新順）"

        filtered["_dt"] = pd.to_datetime(filtered["date"], errors="coerce")
        filtered = filtered.sort_values("_dt", ascending=False)   # index保持（reset_indexしない）

        h1,h2,h3 = st.columns([3,1,1])
        with h1:
            st.markdown(f"<div style='font-size:.98rem;font-weight:700;color:#1a1a2e'>{header} <span style='font-size:.78rem;color:#aaa;font-weight:400'>({len(filtered)}件)</span></div>", unsafe_allow_html=True)
        with h2:
            if st.button("➕ 新規記録", use_container_width=True, key="new2"):
                st.session_state.mode="new_record"; st.rerun()
        with h3:
            if st.button("🛞 見積作成", use_container_width=True, key="quote2"):
                st.session_state.mode="quote"; st.rerun()

        if filtered.empty:
            st.markdown("<div style='padding:36px;text-align:center;color:#ccc;border:1px dashed #e0e0e0;border-radius:14px;margin-top:10px'>記録が見つかりません</div>", unsafe_allow_html=True)
        else:
            def mk_badge(text: str, cls: str) -> str:
                return f'<span class="badge {cls}">{text}</span>' if text else ""

            # テーブルヘッダー
            hcols = st.columns([1.0,1.0,0.75,1.6,1.6,0.85,1.1,0.95,1.8,0.55,0.55])
            for hc, lb in zip(hcols, ["日付","目的","種別","ナンバー","車両","カラー","タイヤ","客層","備考","","編集"]):
                hc.markdown(f"<div style='font-size:.69rem;font-weight:700;color:#aaa;padding-bottom:5px;border-bottom:2px solid #e8e8e8'>{lb}</div>", unsafe_allow_html=True)

            for orig_idx, row in filtered.iterrows():
                plate_str = " ".join(filter(None,[row["plate_area"],row["plate_3digit"],row["plate_kana"],row["plate_num"]]))
                car_str   = " ".join(filter(None,[row["maker"],row["car_model"]]))
                date_s    = str(row["date"])[:10] if row["date"] else ""
                age_s     = row["age"] if row["age"] not in ("","(未選択)") else ""
                gender_b  = mk_badge(row["gender"], f"bg-{row['gender']}")
                purpose_b = mk_badge(row["purpose"], "bp")
                ctype_b   = mk_badge(row["cust_type"], f"bt-{row['cust_type']}")

                rcols = st.columns([1.0,1.0,0.75,1.6,1.6,0.85,1.1,0.95,1.8,0.55,0.55])
                rcols[0].markdown(f"<div style='font-size:.76rem;color:#bbb;padding-top:5px'>{date_s}</div>", unsafe_allow_html=True)
                rcols[1].markdown(purpose_b, unsafe_allow_html=True)
                rcols[2].markdown(ctype_b, unsafe_allow_html=True)
                rcols[3].markdown(f"<div style='font-size:.81rem;font-weight:600'>{plate_str}</div>", unsafe_allow_html=True)
                rcols[4].markdown(f"<div style='font-size:.81rem'>{car_str}</div>", unsafe_allow_html=True)
                rcols[5].markdown(f"<div style='font-size:.78rem;color:#888'>{row['color']}</div>", unsafe_allow_html=True)
                rcols[6].markdown(f"<div style='font-size:.78rem;color:#888'>{row['tire_size']}</div>", unsafe_allow_html=True)
                rcols[7].markdown(f"{gender_b} <span style='font-size:.73rem;color:#aaa'>{age_s}</span>", unsafe_allow_html=True)
                rcols[8].markdown(f"<div style='font-size:.74rem;color:#999;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>{row['memo']}</div>", unsafe_allow_html=True)
                if rcols[9].button("詳細", key=f"det_{orig_idx}", use_container_width=True):
                    st.session_state.mode="view_record"; st.session_state.view_idx=int(orig_idx); st.rerun()
                if rcols[10].button("編集", key=f"edt_{orig_idx}", use_container_width=True):
                    st.session_state.mode="edit_record"; st.session_state.edit_idx=int(orig_idx); st.rerun()

                st.markdown("<div style='border-bottom:1px solid #f2f2f2;margin:0 0 2px 0'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════════
    #  🔍 詳細表示
    # ════════════════════════════════════════════════════════════════════════════
    elif mode == "view_record":
        df  = load_history()
        idx = st.session_state.view_idx
        if idx is None or idx not in df.index:
            st.session_state.mode="list"; st.rerun()
        row = df.loc[idx]

        bc1, bc2 = st.columns([1,1])
        with bc1:
            if st.button("← 一覧に戻る", key="back"):
                st.session_state.mode="list"; st.rerun()
        with bc2:
            if st.button("✏️ この記録を編集", use_container_width=True, key="to_edit"):
                st.session_state.mode="edit_record"; st.session_state.edit_idx=idx; st.rerun()

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        plate_str = " ".join(filter(None,[row["plate_area"],row["plate_3digit"],row["plate_kana"],row["plate_num"]]))
        car_str   = " ".join(filter(None,[row["maker"],row["car_model"]]))

        def badge(text:str,cls:str)->str: return f'<span class="badge {cls}">{text}</span>' if text else ""

        ctype_b  = badge(row["cust_type"], f"bt-{row['cust_type']}")
        gender_b = badge(row["gender"],    f"bg-{row['gender']}")
        purp_b   = badge(row["purpose"],   "bp")
        tire_full = " ".join(filter(None,[row["tire_size"],row["tire_maker"],row["tire_product"]]))
        tyear_s   = f"{row['tire_year']}年製" if row["tire_year"] else ""
        age_s     = row["age"] if row["age"] not in ("","(未選択)") else ""
        memo_html = f'<div class="memo-box">📝 {row["memo"]}</div>' if row["memo"] else ""

        st.markdown(f"""
        <div class="detail-card">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
                <span style="font-size:1.3rem;font-weight:800;color:#1a1a2e">{plate_str}</span>
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
        </div>""", unsafe_allow_html=True)

        same = df[(df["plate_num"] == row["plate_num"]) & (df.index != idx)]
        if not same.empty:
            st.markdown(f"<div class='sec-title'>同一車番の過去記録（{len(same)}件）</div>", unsafe_allow_html=True)
            for _, pr in same.sort_values(by=df.columns[0], ascending=False).iterrows():
                pr_purp = badge(pr["purpose"],"bp")
                pr_car  = " ".join(filter(None,[pr["maker"],pr["car_model"]]))
                st.markdown(f"""
                <div style="padding:10px 14px;border:1px solid #ebebeb;border-left:4px solid #a5b4fc;border-radius:0 12px 12px 0;margin-bottom:7px;background:#fff">
                    <div style="font-size:.74rem;color:#aaa;margin-bottom:3px">{pr['date']}</div>
                    <div style="font-size:.86rem;font-weight:600">{pr_purp} &nbsp;{pr_car}</div>
                    <div style="font-size:.78rem;color:#888;margin-top:2px">{pr['memo']}</div>
                </div>""", unsafe_allow_html=True)
