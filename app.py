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

# ── 見積HTML生成（定価 vs 提案価格 2列） ────────────────────────────────────
def generate_estimate_html(
    tire_maker: str, tire_product: str, tire_size: str,
    retail_price: int, offer_price: int,
    qty: int, labor_unit: int, disp_unit: int,
    plate: str, memo: str
) -> str:
    labor_t  = labor_unit * qty
    disp_t   = disp_unit  * qty
    # 定価
    r_tire   = retail_price * qty
    r_sub    = r_tire + labor_t + disp_t
    r_tax    = int(r_sub * 0.10)
    r_total  = r_sub + r_tax
    # 提案価格
    o_tire   = offer_price * qty
    o_sub    = o_tire + labor_t + disp_t
    o_tax    = int(o_sub * 0.10)
    o_total  = o_sub + o_tax
    # お得額
    savings  = r_total - o_total
    save_pct = round(savings / r_total * 100, 1) if r_total > 0 else 0
    date_str = datetime.now().strftime("%Y年%m月%d日")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<style>
/* ── 印刷背景色を確実に出力 ── */
* {{ -webkit-print-color-adjust:exact!important;
     print-color-adjust:exact!important;
     color-adjust:exact!important;
     box-sizing:border-box; margin:0; padding:0; }}
@page {{ size:A4 portrait; margin:10mm 12mm; }}
body {{ font-family:'Hiragino Kaku Gothic ProN','Yu Gothic','MS Gothic',sans-serif;
        font-size:10pt; color:#1a1a2e; background:#fff; }}
@media print {{ .noprint{{ display:none!important; }} }}

/* ── ヘッダー（緑） ── */
.est-header {{
  background:#1B5E20; color:#fff;
  padding:11px 16px; display:flex; justify-content:space-between; align-items:center;
  border-radius:4px 4px 0 0;
}}
.est-header-title {{ font-size:16pt; font-weight:800; letter-spacing:.05em; }}
.est-doc-title {{
  font-size:12.5pt; font-weight:700; color:#1B5E20;
  text-align:center; padding:9px 0 5px; border-bottom:2.5px solid #1B5E20;
  letter-spacing:.15em;
}}
.doc-no {{ font-size:8pt; color:#999; text-align:right; margin:3px 0 6px; }}

/* ── 顧客情報帯（緑枠） ── */
.cust-box {{
  display:grid; grid-template-columns:1fr 1fr 1fr 1fr;
  border:1.5px solid #1B5E20; border-radius:4px; margin:6px 0 8px;
}}
.cust-cell {{ padding:6px 10px; border-right:1px solid #1B5E20; }}
.cust-cell:last-child {{ border-right:none; }}
.cust-label {{ font-size:7.5pt; color:#666; margin-bottom:2px; }}
.cust-val   {{ font-size:10.5pt; font-weight:700; }}

/* ── 2列比較テーブル ── */
.compare-wrap {{ display:grid; grid-template-columns:1fr 1fr; gap:6px; margin:8px 0; }}
.price-col {{ border-radius:6px; overflow:hidden; }}
.col-header {{ padding:7px 10px; font-size:9pt; font-weight:800; text-align:center; }}
.col-header-retail  {{ background:#607D8B; color:#fff; }}
.col-header-offer   {{ background:#1B5E20; color:#fff; }}
.col-body {{ padding:0; }}
.price-row {{ display:flex; justify-content:space-between; padding:6px 10px;
              border-bottom:1px solid rgba(0,0,0,.08); font-size:9.5pt; }}
.price-row:last-child {{ border-bottom:none; }}
.pr-label {{ color:#555; }}
.pr-val   {{ font-weight:600; }}
.col-retail-bg  {{ background:#ECEFF1; }}
.col-offer-bg   {{ background:#E8F5E9; }}
.col-retail-total {{ background:#B0BEC5; padding:8px 10px;
                     display:flex; justify-content:space-between;
                     font-size:12pt; font-weight:800; color:#263238; }}
.col-offer-total  {{ background:#1B5E20; padding:8px 10px;
                     display:flex; justify-content:space-between;
                     font-size:12pt; font-weight:800; color:#fff; }}

/* ── お得額ボックス（ピンク） ── */
.savings-box {{
  background:#FCE4EC; border:2px solid #E91E63; border-radius:6px;
  padding:10px 16px; margin:8px 0;
  display:flex; justify-content:space-between; align-items:center;
}}
.savings-label {{ font-size:10pt; font-weight:700; color:#880E4F; }}
.savings-amount {{ font-size:18pt; font-weight:800; color:#C62828; }}
.savings-pct    {{ font-size:11pt; font-weight:700; color:#E91E63; margin-left:8px; }}

/* ── 品目明細テーブル（緑枠） ── */
.detail-section {{ margin:8px 0; }}
.detail-title {{ font-size:8.5pt; font-weight:700; color:#1B5E20;
                 border-bottom:1.5px solid #1B5E20; padding-bottom:3px; margin-bottom:4px; }}
table {{ width:100%; border-collapse:collapse; }}
thead tr {{ background:#1B5E20; color:#fff; }}
th {{ padding:6px 8px; font-size:8.5pt; font-weight:700; }}
td {{ padding:6px 8px; border-bottom:1px solid #C8E6C9; font-size:9.5pt; vertical-align:middle; }}
.td-c {{ text-align:center; }}
.td-r {{ text-align:right; }}
.item-main {{ font-weight:600; }}
.item-sub  {{ font-size:7.5pt; color:#777; }}
tr.row-sub {{ background:#F1F8E9; }}
tr.row-tax {{ background:#F1F8E9; }}
tr.row-offer-total td {{
  background:#FCE4EC; border-top:2px solid #C62828;
  font-size:11.5pt; font-weight:800; color:#C62828;
}}

/* ── メモ（ピンク枠） ── */
.memo-section {{ border:1.5px solid #E91E63; border-radius:4px; padding:8px 12px; margin-top:8px; }}
.memo-title   {{ font-size:8pt; font-weight:700; color:#E91E63; margin-bottom:4px; }}
.memo-body    {{ font-size:9.5pt; line-height:1.75; min-height:44px; white-space:pre-wrap; }}

/* ── フッター ── */
.footer {{
  margin-top:14px; border-top:1px solid #ccc; padding-top:6px;
  font-size:8pt; color:#999; display:flex; justify-content:space-between;
}}
.stamp-area {{ border:1px solid #ccc; width:72px; height:44px;
               text-align:center; line-height:44px; font-size:7.5pt; color:#ccc; border-radius:4px; }}

/* ── 印刷ボタン ── */
.print-btn {{
  display:block; margin:10px auto 6px; padding:9px 34px;
  background:#1B5E20; color:#fff; border:none; border-radius:8px;
  font-size:12pt; font-weight:700; cursor:pointer;
}}
.print-btn:hover {{ background:#2E7D32; }}
</style>
</head>
<body>
<button class="print-btn noprint" onclick="window.print()">🖨️ 印刷する</button>

<!-- ヘッダー -->
<div class="est-header">
  <div>
    <div class="est-header-title">⛽ タイヤ御見積書</div>
    <div style="font-size:8.5pt;opacity:.85">GS 接客支援システム</div>
  </div>
  <div style="text-align:right;font-size:9pt">
    発行日：{date_str}<br>担当：___________
  </div>
</div>
<div class="est-doc-title">タ イ ヤ 御 見 積 書</div>
<div class="doc-no">No.{datetime.now().strftime("%Y%m%d%H%M")}</div>

<!-- 顧客情報 -->
<div class="cust-box">
  <div class="cust-cell"><div class="cust-label">車番</div><div class="cust-val">{plate or '　　　　'}</div></div>
  <div class="cust-cell"><div class="cust-label">タイヤメーカー</div><div class="cust-val">{tire_maker or '　　　'}</div></div>
  <div class="cust-cell"><div class="cust-label">商品名</div><div class="cust-val">{tire_product or '　　　'}</div></div>
  <div class="cust-cell"><div class="cust-label">タイヤサイズ</div><div class="cust-val">{tire_size or '　　　'}</div></div>
</div>

<!-- 定価 vs 提案価格 2列比較 -->
<div class="compare-wrap">
  <!-- 定価列 -->
  <div class="price-col">
    <div class="col-header col-header-retail">定価（メーカー希望小売価格）</div>
    <div class="col-body">
      <div class="price-row col-retail-bg"><span class="pr-label">🛞 タイヤ代 {qty}本</span><span class="pr-val">¥{r_tire:,}</span></div>
      <div class="price-row col-retail-bg"><span class="pr-label">🔧 工賃 {qty}本</span><span class="pr-val">¥{labor_t:,}</span></div>
      <div class="price-row col-retail-bg"><span class="pr-label">♻️ 廃タイヤ {qty}本</span><span class="pr-val">¥{disp_t:,}</span></div>
      <div class="price-row col-retail-bg"><span class="pr-label">消費税 10%</span><span class="pr-val">¥{r_tax:,}</span></div>
    </div>
    <div class="col-retail-total"><span>定価合計（税込）</span><span>¥{r_total:,}</span></div>
  </div>
  <!-- 提案価格列 -->
  <div class="price-col">
    <div class="col-header col-header-offer">★ 提案価格（今回のご提案）</div>
    <div class="col-body">
      <div class="price-row col-offer-bg"><span class="pr-label">🛞 タイヤ代 {qty}本</span><span class="pr-val">¥{o_tire:,}</span></div>
      <div class="price-row col-offer-bg"><span class="pr-label">🔧 工賃 {qty}本</span><span class="pr-val">¥{labor_t:,}</span></div>
      <div class="price-row col-offer-bg"><span class="pr-label">♻️ 廃タイヤ {qty}本</span><span class="pr-val">¥{disp_t:,}</span></div>
      <div class="price-row col-offer-bg"><span class="pr-label">消費税 10%</span><span class="pr-val">¥{o_tax:,}</span></div>
    </div>
    <div class="col-offer-total"><span>提案価格合計（税込）</span><span>¥{o_total:,}</span></div>
  </div>
</div>

<!-- お得額（ピンク枠） -->
<div class="savings-box">
  <div>
    <div class="savings-label">🎉 定価との差額（お得額）</div>
    <div style="font-size:8pt;color:#888;margin-top:2px">定価合計 ¥{r_total:,} → 提案価格合計 ¥{o_total:,}</div>
  </div>
  <div>
    <span class="savings-amount">¥{savings:,}</span>
    <span class="savings-pct">({save_pct}% OFF)</span>
  </div>
</div>

<!-- 品目明細（緑枠テーブル） -->
<div class="detail-section">
  <div class="detail-title">■ 品目明細（提案価格ベース）</div>
  <table>
    <thead><tr>
      <th style="width:40%;text-align:left">品名・内容</th>
      <th style="width:8%" class="td-c">数量</th>
      <th style="width:10%" class="td-c">単位</th>
      <th style="width:21%" class="td-r">単価（税抜）</th>
      <th style="width:21%" class="td-r">金額（税抜）</th>
    </tr></thead>
    <tbody>
      <tr>
        <td><div class="item-main">{tire_maker}</div><div class="item-sub">{tire_product}　{tire_size}</div></td>
        <td class="td-c">{qty}</td><td class="td-c">本</td>
        <td class="td-r">¥{offer_price:,}</td><td class="td-r">¥{o_tire:,}</td>
      </tr>
      <tr>
        <td><div class="item-main">タイヤ取付工賃</div></td>
        <td class="td-c">{qty}</td><td class="td-c">本</td>
        <td class="td-r">¥{labor_unit:,}</td><td class="td-r">¥{labor_t:,}</td>
      </tr>
      <tr>
        <td><div class="item-main">廃タイヤ処理料</div></td>
        <td class="td-c">{qty}</td><td class="td-c">本</td>
        <td class="td-r">¥{disp_unit:,}</td><td class="td-r">¥{disp_t:,}</td>
      </tr>
      <tr class="row-sub">
        <td colspan="4" class="td-r">小計（税抜）</td>
        <td class="td-r">¥{o_sub:,}</td>
      </tr>
      <tr class="row-tax">
        <td colspan="4" class="td-r">消費税（10%）</td>
        <td class="td-r">¥{o_tax:,}</td>
      </tr>
      <tr class="row-offer-total">
        <td colspan="4" class="td-r">★ ご請求合計（税込）</td>
        <td class="td-r">¥{o_total:,}</td>
      </tr>
    </tbody>
  </table>
</div>

<!-- 接客メモ（ピンク枠） -->
<div class="memo-section">
  <div class="memo-title">📝 接客メモ・特記事項</div>
  <div class="memo-body">{memo if memo else '　'}</div>
</div>

<!-- フッター -->
<div class="footer">
  <div>
    ※ 本見積の有効期限は発行日より30日間です。<br>
    ※ 定価はメーカー希望小売価格（税込）を参考としています。
  </div>
  <div style="text-align:right"><div class="stamp-area">確認印</div></div>
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

/* 見積カード共通 */
.q-row{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,.07);font-size:.84rem;}
.q-row:last-child{border-bottom:none;}
.q-label{color:#666;}
.q-val{font-weight:600;color:#1a1a2e;}

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

        # ── 共通設定（タイヤ商品 + 本数 + 工賃 + 廃タイヤ + 車番）────────────────
        st.markdown("<div class='sec-title'>タイヤ・共通設定</div>", unsafe_allow_html=True)
        ta1,ta2,ta3 = st.columns([2,2,2])
        with ta1: q_tm = st.selectbox("タイヤメーカー", TIRE_MAKER_OPTIONS, key="q_tm")
        with ta2: q_tp = st.text_input("商品名", placeholder="ENASAVE EC204", key="q_tp")
        with ta3: q_ts = st.text_input("タイヤサイズ", placeholder="195/65R15", key="q_ts")

        tb1,tb2,tb3,tb4 = st.columns(4)
        with tb1: q_qty        = st.selectbox("本数", [4,2,1], key="q_qty")
        with tb2: q_labor_unit = st.number_input("工賃（1本・税抜）", min_value=0, value=2500, step=100, key="q_labor_unit", format="%d")
        with tb3: q_disp_unit  = st.number_input("廃タイヤ（1本）",   min_value=0, value=300,  step=50,  key="q_disp_unit",  format="%d")
        with tb4: q_plate      = st.text_input("車番下4桁（任意）", placeholder="1234", max_chars=4, key="q_plate")

        labor_sub = q_labor_unit * q_qty
        disp_sub  = q_disp_unit  * q_qty

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # ── 定価 vs 提案価格 2列 ─────────────────────────────────────────────
        col_r, col_o = st.columns(2, gap="medium")

        # 定価列（グレー系）
        with col_r:
            st.markdown("<div style='background:linear-gradient(135deg,#eceff1,#cfd8dc);border:1.5px solid #90a4ae;border-radius:14px;padding:14px 16px'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:.9rem;font-weight:800;color:#455a64;margin-bottom:8px'>📋 定価（メーカー希望小売価格）</div>", unsafe_allow_html=True)
            q_retail = st.number_input("定価（1本・税抜）", min_value=0, value=20000, step=500, key="q_retail", format="%d")
            r_tire   = q_retail * q_qty
            r_sub    = r_tire + labor_sub + disp_sub
            r_tax    = int(r_sub * 0.10)
            r_total  = r_sub + r_tax
            st.markdown(f"""
            <div style="margin-top:10px">
            <div class="q-row"><span class="q-label">🛞 タイヤ代（{q_qty}本）</span><span class="q-val">¥{r_tire:,}</span></div>
            <div class="q-row"><span class="q-label">🔧 工賃（{q_qty}本）</span><span class="q-val">¥{labor_sub:,}</span></div>
            <div class="q-row"><span class="q-label">♻️ 廃タイヤ（{q_qty}本）</span><span class="q-val">¥{disp_sub:,}</span></div>
            <div class="q-row"><span class="q-label">消費税（10%）</span><span class="q-val">¥{r_tax:,}</span></div>
            <div style="font-size:1.1rem;font-weight:800;color:#455a64;padding-top:10px;margin-top:6px;border-top:2px solid #90a4ae;display:flex;justify-content:space-between">
                <span>定価合計（税込）</span><span>¥{r_total:,}</span>
            </div>
            </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # 提案価格列（緑系）
        with col_o:
            st.markdown("<div style='background:linear-gradient(135deg,#e8f5e9,#c8e6c9);border:1.5px solid #66bb6a;border-radius:14px;padding:14px 16px'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:.9rem;font-weight:800;color:#2e7d32;margin-bottom:8px'>⭐ 提案価格（今回のご提案）</div>", unsafe_allow_html=True)
            q_offer  = st.number_input("提案価格（1本・税抜）", min_value=0, value=15000, step=500, key="q_offer", format="%d")
            o_tire   = q_offer * q_qty
            o_sub    = o_tire + labor_sub + disp_sub
            o_tax    = int(o_sub * 0.10)
            o_total  = o_sub + o_tax
            st.markdown(f"""
            <div style="margin-top:10px">
            <div class="q-row"><span class="q-label">🛞 タイヤ代（{q_qty}本）</span><span class="q-val">¥{o_tire:,}</span></div>
            <div class="q-row"><span class="q-label">🔧 工賃（{q_qty}本）</span><span class="q-val">¥{labor_sub:,}</span></div>
            <div class="q-row"><span class="q-label">♻️ 廃タイヤ（{q_qty}本）</span><span class="q-val">¥{disp_sub:,}</span></div>
            <div class="q-row"><span class="q-label">消費税（10%）</span><span class="q-val">¥{o_tax:,}</span></div>
            <div style="font-size:1.2rem;font-weight:800;color:#1b5e20;padding-top:10px;margin-top:6px;border-top:2px solid #66bb6a;display:flex;justify-content:space-between">
                <span>提案合計（税込）</span><span>¥{o_total:,}</span>
            </div>
            </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── お得額（ピンク強調ボックス） ──────────────────────────────────────
        savings  = r_total - o_total
        save_pct = round(savings / r_total * 100, 1) if r_total > 0 else 0.0
        save_color = "#c62828" if savings > 0 else "#888"
        savings_html = f"""
        <div style="background:#FCE4EC;border:2px solid #E91E63;border-radius:14px;
                    padding:14px 20px;margin:10px 0;
                    display:flex;justify-content:space-between;align-items:center">
            <div>
                <div style="font-size:.78rem;font-weight:700;color:#880E4F;margin-bottom:4px">🎉 定価との差額（お得額）</div>
                <div style="font-size:.75rem;color:#888">定価 ¥{r_total:,} → 提案価格 ¥{o_total:,}</div>
            </div>
            <div style="text-align:right">
                <span style="font-size:2rem;font-weight:800;color:{save_color}">¥{abs(savings):,}</span>
                <span style="font-size:1.1rem;font-weight:700;color:#e91e63;margin-left:6px">
                    {"" if savings <= 0 else f"({save_pct}% OFF)"}
                </span>
            </div>
        </div>"""
        st.markdown(savings_html, unsafe_allow_html=True)

        # ── A表（3割引ライン）チェック ────────────────────────────────────────
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
                <div style="font-size:.72rem;color:#4b6cb7;font-weight:700;margin-bottom:5px">A表3割引ライン（税抜・工賃込み）</div>
                <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:.82rem">
                    <span>タイヤ: <b>¥{a_tire_line:,}</b></span>
                    <span>工賃: <b>¥{labor_sub:,}</b></span>
                    <span>廃タイヤ: <b>¥{disp_sub:,}</b></span>
                    <span style="font-size:.96rem;font-weight:800;color:#1d4ed8">最低ライン ¥{a_total_line:,}</span>
                </div>
            </div>""", unsafe_allow_html=True)

        # 提案価格でのA表判定（1列のみ）
        diff = o_sub - a_total_line
        ok   = diff >= 0
        if ok:
            st.markdown(f'<div class="acheck-ok" style="margin-top:6px"><div style="font-size:1.2rem">✅</div><div style="font-weight:700;color:#166534">提案価格　利益あり（A表ライン +¥{diff:,}）</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="acheck-ng" style="margin-top:6px"><div style="font-size:1.2rem">❌</div><div style="font-weight:700;color:#991b1b">提案価格　赤字注意（A表ライン -¥{abs(diff):,} 不足）</div></div>', unsafe_allow_html=True)

        # ── 接客メモ ──────────────────────────────────────────────────────────
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown("<div class='sec-title'>✏️ 接客メモ（殴り書きOK）</div>", unsafe_allow_html=True)
        st.markdown("<div style='background:#fffde7;border:1.5px solid #f9d71c;border-radius:10px;padding:4px 8px'>", unsafe_allow_html=True)
        q_memo = st.text_area("接客メモ", placeholder="お客様要望・タイヤ状態・次回案内など", height=140, key="q_memo", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── 見積書プレビュー・印刷 ────────────────────────────────────────────
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown("<div class='sec-title'>🖨️ 見積書印刷</div>", unsafe_allow_html=True)
        pr1, pr2 = st.columns([2, 1])
        with pr2:
            do_print = st.button("📄 見積書プレビュー・印刷", use_container_width=True, key="do_print")

        if do_print or st.session_state.get("show_print"):
            st.session_state["show_print"] = True
            html_str = generate_estimate_html(
                opt(q_tm), q_tp, q_ts,
                q_retail, q_offer,
                q_qty, q_labor_unit, q_disp_unit,
                q_plate, q_memo
            )
            components.html(html_str, height=1080, scrolling=True)
            if st.button("プレビューを閉じる", key="close_print"):
                st.session_state["show_print"] = False; st.rerun()
        else:
            st.session_state["show_print"] = False

        # ── 保存ボタン ────────────────────────────────────────────────────────
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        sv_a, sv_b = st.columns(2)

        def build_quote_row() -> dict:
            note = (f"【タイヤ見積】{opt(q_tm)} {q_tp} {q_ts} / {q_qty}本 "
                    f"/ 定価¥{q_retail:,}→提案¥{q_offer:,}/本 / 税込¥{o_total:,} "
                    f"/ お得額¥{savings:,}"
                    + (f"\n{q_memo}" if q_memo else ""))
            return {"date":datetime.now().strftime("%Y/%m/%d %H:%M"),"purpose":"タイヤ見積",
                    "cust_type":"","plate_area":"","plate_3digit":"","plate_kana":"",
                    "plate_num":q_plate,"maker":"","car_model":"","color":"","age":"","gender":"",
                    "tire_size":q_ts,"tire_size_num":tire_to_num(q_ts),
                    "tire_year":"","tire_maker":opt(q_tm),"tire_product":q_tp,"memo":note}

        with sv_a:
            if st.button("📋 見積を履歴に保存", type="primary", use_container_width=True, key="save_quote"):
                append_record(build_quote_row())
                st.success("見積を保存しました！"); st.session_state.mode="list"; st.session_state.searched_plate=q_plate or ""; st.rerun()
        with sv_b:
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
