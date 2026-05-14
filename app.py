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
SCHEDULE_COLS    = ["id","date","time","title","detail","status","plate_num","cust_type"]
TIRE_PRICES_CSV  = BASE_DIR / "tire_prices.csv"
TIRE_PRICE_COLS  = ["size","product_name","retail_price"]

PRESET_LABELS = [
    "① 標準（定価+工賃+廃タイヤ）",
    "② 税抜化（タイヤのみ税抜換算）",
    "③ 工賃サービス（工賃0円）",
    "④ 諸費用サービス（工賃+廃タイヤ0円）",
    "⑤ A表価格（定価70%+諸費用0円）",
]
STD_LABOR = 1650   # 標準工賃（税込/本）
STD_DISP  = 550    # 廃タイヤ料（税込/本）

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

def load_tire_prices() -> pd.DataFrame:
    sample = [
        # 155/65R14
        ("155/65R14","ECOPIA EP150",12650),("155/65R14","NEWNO",11000),("155/65R14","セイバーリング SL201",8250),
        # 165/65R13
        ("165/65R13","ECOPIA EP150",11000),("165/65R13","セイバーリング SL201",7700),
        # 175/65R14
        ("175/65R14","ECOPIA EP300",14300),("175/65R14","NEWNO",12100),("175/65R14","セイバーリング SL201",8800),
        # 185/65R15
        ("185/65R15","REGNO GR-XIII",19800),("185/65R15","ECOPIA EP300",15400),("185/65R15","NEWNO",12650),("185/65R15","セイバーリング SL201",9350),
        # 195/65R15
        ("195/65R15","REGNO GR-XIII",21450),("195/65R15","ECOPIA EP300",17050),("195/65R15","NEWNO",14300),("195/65R15","セイバーリング SL201",9900),
        # 205/55R16
        ("205/55R16","REGNO GR-XIII",24750),("205/55R16","ECOPIA EP300",20350),("205/55R16","NEWNO",16500),("205/55R16","セイバーリング SL201",11550),
        # 205/60R16
        ("205/60R16","REGNO GR-XIII",23100),("205/60R16","ECOPIA EP300",18700),("205/60R16","NEWNO",15400),("205/60R16","セイバーリング SL201",10450),
        # 215/45R17
        ("215/45R17","REGNO GR-XIII",28600),("215/45R17","ECOPIA EP300",23100),("215/45R17","POTENZA Sport",39600),("215/45R17","セイバーリング SL501",13200),
        # 215/50R17
        ("215/50R17","REGNO GR-XIII",27500),("215/50R17","ECOPIA EP300",22000),("215/50R17","NEWNO",18150),("215/50R17","セイバーリング SL501",12650),
        # 215/55R17
        ("215/55R17","REGNO GR-XIII",26400),("215/55R17","ECOPIA EP300",21450),("215/55R17","NEWNO",17600),("215/55R17","セイバーリング SL201",12100),
        # 225/45R18
        ("225/45R18","REGNO GR-XIII",33000),("225/45R18","ECOPIA EP300",27500),("225/45R18","POTENZA Sport",44000),("225/45R18","セイバーリング SL501",15400),
        # 225/50R18
        ("225/50R18","REGNO GR-XIII",31900),("225/50R18","ECOPIA EP300",26400),("225/50R18","POTENZA Sport",42900),("225/50R18","セイバーリング SL501",14850),
        # 225/55R18
        ("225/55R18","REGNO GR-XIII",30800),("225/55R18","ECOPIA EP300",25300),("225/55R18","ALENZA 001",38500),("225/55R18","セイバーリング SL201",14300),
        # 235/50R18
        ("235/50R18","REGNO GR-XIII",34100),("235/50R18","POTENZA Sport",46200),("235/50R18","ALENZA 001",39600),("235/50R18","セイバーリング SL501",16500),
        # 245/40R19
        ("245/40R19","REGNO GR-XIII",39600),("245/40R19","POTENZA Sport",55000),("245/40R19","セイバーリング SL501",20900),
        # 165/60R15 (軽SUV)
        ("165/60R15","ECOPIA EP150",14850),("165/60R15","NEWNO",12650),("165/60R15","セイバーリング SL201",9900),
    ]
    if not TIRE_PRICES_CSV.exists():
        df = pd.DataFrame(sample, columns=TIRE_PRICE_COLS)
        df.to_csv(TIRE_PRICES_CSV, index=False)
        return df
    df = pd.read_csv(TIRE_PRICES_CSV, dtype=str).fillna("")
    for c in TIRE_PRICE_COLS:
        if c not in df.columns: df[c] = ""
    return df[TIRE_PRICE_COLS]

def tire_to_num(s: str) -> str:
    return re.sub(r"[^\d]", "", s)

def opt(v: str) -> str:
    return "" if v == "(未選択)" else v

def sel_idx(options: list, val: str) -> int:
    return options.index(val) if val in options else 0

# ── 見積HTML生成（全額税込・定価 vs 提案価格 2列） ──────────────────────────
def generate_estimate_html(
    tire_maker: str, tire_product: str, tire_size: str,
    retail_unit: int,   # 定価/本（税込）
    offer_unit: int,    # 提示タイヤ単価/本（税込）
    offer_labor: int,   # 提示工賃/本（税込）
    offer_disp: int,    # 提示廃タイヤ/本（税込）
    qty: int,
    plate: str, customer: str, staff: str,
    maker: str, car_model: str, memo: str
) -> str:
    # 定価列（タイヤ定価 + 標準工賃 + 標準廃タイヤ、全て税込）
    r_tire  = retail_unit * qty
    r_labor = STD_LABOR   * qty
    r_disp  = STD_DISP    * qty
    r_total = r_tire + r_labor + r_disp
    # 提示価格列（全て税込）
    o_tire  = offer_unit  * qty
    o_labor = offer_labor * qty
    o_disp  = offer_disp  * qty
    o_total = o_tire + o_labor + o_disp
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
    発行日：{date_str}<br>担当：{staff or '___________'}
  </div>
</div>
<div class="est-doc-title">タ イ ヤ 御 見 積 書</div>
<div class="doc-no">No.{datetime.now().strftime("%Y%m%d%H%M")}</div>

<!-- 顧客情報 -->
<div class="cust-box">
  <div class="cust-cell"><div class="cust-label">車番</div><div class="cust-val">{plate or '　　　'}</div></div>
  <div class="cust-cell"><div class="cust-label">お客様</div><div class="cust-val">{customer or '　　　'}</div></div>
  <div class="cust-cell"><div class="cust-label">担当者</div><div class="cust-val">{staff or '　　　'}</div></div>
  <div class="cust-cell"><div class="cust-label">タイヤ</div><div class="cust-val">{tire_maker} {tire_product} {tire_size}</div></div>
</div>

<!-- 定価 vs 提案価格 2列比較 -->
<div class="compare-wrap">
  <!-- 定価列 -->
  <div class="price-col">
    <div class="col-header col-header-retail">定価（メーカー希望小売価格）</div>
    <div class="col-body">
      <div class="price-row col-retail-bg"><span class="pr-label">🛞 タイヤ代 {qty}本</span><span class="pr-val">¥{r_tire:,}</span></div>
      <div class="price-row col-retail-bg"><span class="pr-label">🔧 工賃 {qty}本</span><span class="pr-val">¥{r_labor:,}</span></div>
      <div class="price-row col-retail-bg"><span class="pr-label">♻️ 廃タイヤ {qty}本</span><span class="pr-val">¥{r_disp:,}</span></div>
    </div>
    <div class="col-retail-total"><span>定価合計（税込）</span><span>¥{r_total:,}</span></div>
  </div>
  <!-- 提案価格列 -->
  <div class="price-col">
    <div class="col-header col-header-offer">★ 提案価格（今回のご提案）</div>
    <div class="col-body">
      <div class="price-row col-offer-bg"><span class="pr-label">🛞 タイヤ代 {qty}本</span><span class="pr-val">¥{o_tire:,}</span></div>
      <div class="price-row col-offer-bg"><span class="pr-label">🔧 工賃 {qty}本</span><span class="pr-val">¥{o_labor:,}</span></div>
      <div class="price-row col-offer-bg"><span class="pr-label">♻️ 廃タイヤ {qty}本</span><span class="pr-val">¥{o_disp:,}</span></div>
    </div>
    <div class="col-offer-total"><span>提示価格合計（税込）</span><span>¥{o_total:,}</span></div>
  </div>
</div>

<!-- お得額（ピンク枠） -->
<div class="savings-box">
  <div>
    <div class="savings-label">🎉 定価との差額（お得額）</div>
    <div style="font-size:8pt;color:#888;margin-top:2px">定価合計 ¥{r_total:,} → 提示価格合計 ¥{o_total:,}</div>
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
      <th style="width:21%" class="td-r">単価（税込）</th>
      <th style="width:21%" class="td-r">金額（税込）</th>
    </tr></thead>
    <tbody>
      <tr>
        <td><div class="item-main">{tire_maker}</div><div class="item-sub">{tire_product}　{tire_size}</div></td>
        <td class="td-c">{qty}</td><td class="td-c">本</td>
        <td class="td-r">¥{offer_unit:,}</td><td class="td-r">¥{o_tire:,}</td>
      </tr>
      <tr>
        <td><div class="item-main">タイヤ取付工賃</div></td>
        <td class="td-c">{qty}</td><td class="td-c">本</td>
        <td class="td-r">¥{offer_labor:,}</td><td class="td-r">¥{o_labor:,}</td>
      </tr>
      <tr>
        <td><div class="item-main">廃タイヤ処理料</div></td>
        <td class="td-c">{qty}</td><td class="td-c">本</td>
        <td class="td-r">¥{offer_disp:,}</td><td class="td-r">¥{o_disp:,}</td>
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
    # quote 2-step flow
    "quote_step": "hearing",
    "q_hearing_plate": "",
    "q_hearing_maker": "",
    "q_hearing_model": "",
    "q_hearing_customer": "",
    "q_hearing_staff": "",
    "q_hearing_size": "",
    "q_preset_idx": 0,
    # duplicate flow
    "is_duplicate": False,
    "duplicate_data": {},
    # delete flow
    "confirm_delete_idx": None,
    "deleted_message": "",
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

/* 削除ボタン（13列テーブルの最終列） */
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(13)) [data-testid="column"]:nth-child(13) [data-testid="stButton"]>button{background:#fff0f0!important;border:1.5px solid #fca5a5!important;color:#b91c1c!important;font-weight:700!important;}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(13)) [data-testid="column"]:nth-child(13) [data-testid="stButton"]>button:hover{background:#ef4444!important;border-color:#dc2626!important;color:#fff!important;}
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
        quote_step = st.session_state.get("quote_step", "hearing")

        if st.button("← 戻る", key="quote_back"):
            if quote_step == "detail":
                st.session_state.quote_step = "hearing"; st.rerun()
            else:
                st.session_state.mode = "list"; st.session_state.quote_step = "hearing"; st.rerun()

        # ── STEP 1: ヒアリング ────────────────────────────────────────────────
        if quote_step == "hearing":
            st.markdown("<div style='font-size:1rem;font-weight:800;color:#1a1a2e;margin:6px 0 2px'>🛞 タイヤ見積 STEP 1 — ヒアリング</div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:.8rem;color:#aaa;margin-bottom:14px'>お客様情報とタイヤサイズを入力してください</div>", unsafe_allow_html=True)

            with st.form("hearing_form"):
                h1, h2, h3 = st.columns(3)
                with h1: hf_plate    = st.text_input("🚗 車番下4桁（任意）", placeholder="1234", max_chars=4)
                with h2: hf_maker    = st.text_input("🏭 メーカー（任意）", placeholder="トヨタ")
                with h3: hf_model    = st.text_input("🚙 車種（任意）", placeholder="プリウス")
                h4, h5, h6 = st.columns(3)
                with h4: hf_customer = st.text_input("👤 お客様名（任意）", placeholder="山田 太郎 様")
                with h5: hf_staff    = st.text_input("👷 担当者名（必須）", placeholder="田中")
                with h6: hf_size     = st.text_input("🛞 タイヤサイズ（必須）", placeholder="195/65R15")
                next_btn = st.form_submit_button("見積を作成する →", type="primary", use_container_width=True)

            if next_btn:
                if not hf_staff or not hf_size:
                    st.error("担当者名とタイヤサイズは必須です")
                else:
                    st.session_state.q_hearing_plate    = hf_plate
                    st.session_state.q_hearing_maker    = hf_maker
                    st.session_state.q_hearing_model    = hf_model
                    st.session_state.q_hearing_customer = hf_customer
                    st.session_state.q_hearing_staff    = hf_staff
                    st.session_state.q_hearing_size     = hf_size
                    st.session_state.quote_step = "detail"
                    st.session_state.q_preset_idx = 0
                    st.rerun()

        # ── STEP 2: 見積詳細 ──────────────────────────────────────────────────
        else:
            hs_plate    = st.session_state.get("q_hearing_plate", "")
            hs_maker    = st.session_state.get("q_hearing_maker", "")
            hs_model    = st.session_state.get("q_hearing_model", "")
            hs_customer = st.session_state.get("q_hearing_customer", "")
            hs_staff    = st.session_state.get("q_hearing_staff", "")
            hs_size     = st.session_state.get("q_hearing_size", "")

            # ヒアリング情報帯
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#e8f5e9,#f1f8e9);border:1.5px solid #66bb6a;
                        border-radius:14px;padding:12px 16px;margin-bottom:14px;
                        display:grid;grid-template-columns:1fr 1fr 1fr 1fr 1fr;gap:8px">
                <div><div style="font-size:.68rem;color:#666;margin-bottom:2px">車番</div>
                     <div style="font-weight:700;color:#1a1a2e">{hs_plate or '－'}</div></div>
                <div><div style="font-size:.68rem;color:#666;margin-bottom:2px">車両</div>
                     <div style="font-weight:700;color:#1a1a2e">{(hs_maker+' '+hs_model).strip() or '－'}</div></div>
                <div><div style="font-size:.68rem;color:#666;margin-bottom:2px">お客様</div>
                     <div style="font-weight:700;color:#1a1a2e">{hs_customer or '－'}</div></div>
                <div><div style="font-size:.68rem;color:#666;margin-bottom:2px">担当</div>
                     <div style="font-weight:700;color:#1a1a2e">{hs_staff}</div></div>
                <div><div style="font-size:.68rem;color:#666;margin-bottom:2px">タイヤサイズ</div>
                     <div style="font-weight:700;color:#2563eb">{hs_size}</div></div>
            </div>""", unsafe_allow_html=True)

            st.markdown("<div style='font-size:1rem;font-weight:800;color:#1a1a2e;margin:0 0 8px 0'>🛞 STEP 2 — 見積詳細</div>", unsafe_allow_html=True)

            # タイヤ商品選択
            tire_df = load_tire_prices()
            tire_df["retail_price"] = pd.to_numeric(tire_df["retail_price"], errors="coerce").fillna(0).astype(int)
            matched = tire_df[tire_df["size"] == hs_size]

            td1, td2, td3 = st.columns([2, 2, 1])
            with td1:
                q_tm = st.selectbox("タイヤメーカー", TIRE_MAKER_OPTIONS, key="q_tm")

            if matched.empty:
                st.warning(f"「{hs_size}」に一致する商品がありません。商品名と定価を手動入力してください。")
                with td2:
                    q_tp = st.text_input("商品名", placeholder="ECOPIA EP300", key="q_tp")
                with td3:
                    retail_price = st.number_input("定価/本（税込）", min_value=0, value=0, step=500, key="q_retail_manual", format="%d")
            else:
                products = matched["product_name"].tolist()
                with td2:
                    q_tp = st.selectbox("商品名（サイズ自動絞込）", products, key="q_tp")
                row_match = matched[matched["product_name"] == q_tp]
                retail_price = int(row_match["retail_price"].iloc[0]) if not row_match.empty else 0
                with td3:
                    st.markdown(f"""
                    <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;
                                padding:8px 12px;margin-top:22px;text-align:center">
                        <div style="font-size:.7rem;color:#666;margin-bottom:2px">定価/本（税込）</div>
                        <div style="font-size:1.1rem;font-weight:800;color:#1B5E20">¥{retail_price:,}</div>
                    </div>""", unsafe_allow_html=True)

            q_qty    = st.selectbox("本数", [4, 2, 1], key="q_qty")
            a_price  = round(retail_price * 0.70)

            st.markdown("<hr class='divider'>", unsafe_allow_html=True)
            st.markdown("<div class='sec-title'>⚡ 値引きプリセット</div>", unsafe_allow_html=True)
            preset_idx = st.radio(
                "プリセット選択",
                options=list(range(len(PRESET_LABELS))),
                format_func=lambda i: PRESET_LABELS[i],
                key="q_preset_radio",
                horizontal=False,
                label_visibility="collapsed",
            )
            preset_key = str(preset_idx)

            if preset_idx == 0:
                default_ou, default_ol, default_od = retail_price, STD_LABOR, STD_DISP
            elif preset_idx == 1:
                default_ou, default_ol, default_od = round(retail_price / 1.1), STD_LABOR, STD_DISP
            elif preset_idx == 2:
                default_ou, default_ol, default_od = retail_price, 0, STD_DISP
            elif preset_idx == 3:
                default_ou, default_ol, default_od = retail_price, 0, 0
            else:
                default_ou, default_ol, default_od = a_price, 0, 0

            st.markdown("<div class='sec-title'>📝 提示価格（1本あたり・税込）</div>", unsafe_allow_html=True)
            ni1, ni2, ni3 = st.columns(3)
            with ni1:
                offer_unit  = st.number_input("🛞 提示タイヤ単価/本（税込）", min_value=0, value=default_ou, step=100, key=f"ou_{preset_key}", format="%d")
            with ni2:
                offer_labor = st.number_input("🔧 提示工賃/本（税込）",       min_value=0, value=default_ol, step=100, key=f"ol_{preset_key}", format="%d")
            with ni3:
                offer_disp  = st.number_input("♻️ 提示廃タイヤ/本（税込）",   min_value=0, value=default_od, step=50,  key=f"od_{preset_key}", format="%d")

            if retail_price > 0 and offer_unit < a_price:
                st.markdown(f"""
                <div class="acheck-ng" style="margin:6px 0">
                    <div style="font-size:1rem">⚠️ <b>A表割れ注意</b></div>
                    <div style="font-size:.82rem;color:#991b1b;margin-top:4px">
                        提示単価 ¥{offer_unit:,} ＜ A表価格 ¥{a_price:,}（定価70%）&nbsp;／&nbsp;差額 <b>-¥{a_price - offer_unit:,}</b>/本
                    </div>
                </div>""", unsafe_allow_html=True)
            elif retail_price > 0:
                st.markdown(f'<div class="acheck-ok" style="margin:6px 0">✅ A表クリア（A表価格 ¥{a_price:,} 以上）</div>', unsafe_allow_html=True)

            r_tire  = retail_price * q_qty
            r_labor = STD_LABOR    * q_qty
            r_disp  = STD_DISP     * q_qty
            r_total = r_tire + r_labor + r_disp
            o_tire  = offer_unit  * q_qty
            o_labor = offer_labor * q_qty
            o_disp  = offer_disp  * q_qty
            o_total = o_tire + o_labor + o_disp
            savings  = r_total - o_total
            save_pct = round(savings / r_total * 100, 1) if r_total > 0 else 0.0

            st.markdown("<hr class='divider'>", unsafe_allow_html=True)
            col_r, col_o = st.columns(2, gap="medium")
            with col_r:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#eceff1,#cfd8dc);border:1.5px solid #90a4ae;border-radius:14px;padding:14px 16px">
                <div style="font-size:.9rem;font-weight:800;color:#455a64;margin-bottom:8px">📋 定価（税込）</div>
                <div class="q-row"><span class="q-label">🛞 タイヤ代（{q_qty}本）</span><span class="q-val">¥{r_tire:,}</span></div>
                <div class="q-row"><span class="q-label">🔧 工賃（{q_qty}本）</span><span class="q-val">¥{r_labor:,}</span></div>
                <div class="q-row"><span class="q-label">♻️ 廃タイヤ（{q_qty}本）</span><span class="q-val">¥{r_disp:,}</span></div>
                <div style="font-size:1.1rem;font-weight:800;color:#455a64;padding-top:10px;margin-top:6px;border-top:2px solid #90a4ae;display:flex;justify-content:space-between">
                    <span>定価合計（税込）</span><span>¥{r_total:,}</span>
                </div>
                </div>""", unsafe_allow_html=True)
            with col_o:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#e8f5e9,#c8e6c9);border:1.5px solid #66bb6a;border-radius:14px;padding:14px 16px">
                <div style="font-size:.9rem;font-weight:800;color:#2e7d32;margin-bottom:8px">⭐ 提示価格（税込）</div>
                <div class="q-row"><span class="q-label">🛞 タイヤ代（{q_qty}本）</span><span class="q-val">¥{o_tire:,}</span></div>
                <div class="q-row"><span class="q-label">🔧 工賃（{q_qty}本）</span><span class="q-val">¥{o_labor:,}</span></div>
                <div class="q-row"><span class="q-label">♻️ 廃タイヤ（{q_qty}本）</span><span class="q-val">¥{o_disp:,}</span></div>
                <div style="font-size:1.2rem;font-weight:800;color:#1b5e20;padding-top:10px;margin-top:6px;border-top:2px solid #66bb6a;display:flex;justify-content:space-between">
                    <span>提示合計（税込）</span><span>¥{o_total:,}</span>
                </div>
                </div>""", unsafe_allow_html=True)

            save_color = "#c62828" if savings > 0 else "#888"
            st.markdown(f"""
            <div style="background:#FCE4EC;border:2px solid #E91E63;border-radius:14px;
                        padding:14px 20px;margin:10px 0;
                        display:flex;justify-content:space-between;align-items:center">
                <div>
                    <div style="font-size:.78rem;font-weight:700;color:#880E4F;margin-bottom:4px">🎉 定価との差額（お得額）</div>
                    <div style="font-size:.75rem;color:#888">定価 ¥{r_total:,} → 提示価格 ¥{o_total:,}</div>
                </div>
                <div style="text-align:right">
                    <span style="font-size:2rem;font-weight:800;color:{save_color}">¥{abs(savings):,}</span>
                    <span style="font-size:1.1rem;font-weight:700;color:#e91e63;margin-left:6px">
                        {"" if savings <= 0 else f"({save_pct}% OFF)"}
                    </span>
                </div>
            </div>""", unsafe_allow_html=True)

            st.markdown("<hr class='divider'>", unsafe_allow_html=True)
            st.markdown("<div class='sec-title'>✏️ 接客メモ</div>", unsafe_allow_html=True)
            q_memo = st.text_area("接客メモ", placeholder="お客様要望・タイヤ状態・次回案内など", height=100, key="q_memo", label_visibility="collapsed")

            st.markdown("<hr class='divider'>", unsafe_allow_html=True)
            pa, pb, pc = st.columns(3)
            with pa:
                do_print = st.button("📄 見積書プレビュー・印刷", use_container_width=True, key="do_print")
            with pb:
                do_save = st.button("📋 履歴に保存", type="primary", use_container_width=True, key="save_quote")
            with pc:
                if st.button("閉じる", use_container_width=True, key="close_quote"):
                    st.session_state.mode = "list"; st.session_state.quote_step = "hearing"; st.rerun()

            if do_print or st.session_state.get("show_print"):
                st.session_state["show_print"] = True
                html_str = generate_estimate_html(
                    opt(q_tm), q_tp, hs_size,
                    retail_price, offer_unit, offer_labor, offer_disp,
                    q_qty,
                    hs_plate, hs_customer, hs_staff,
                    hs_maker, hs_model, q_memo
                )
                components.html(html_str, height=1080, scrolling=True)
                if st.button("プレビューを閉じる", key="close_print"):
                    st.session_state["show_print"] = False; st.rerun()
            else:
                st.session_state["show_print"] = False

            if do_save:
                note = (f"【タイヤ見積】{opt(q_tm)} {q_tp} {hs_size} / {q_qty}本 "
                        f"/ 定価¥{retail_price:,}→提示¥{offer_unit:,}/本 / 合計¥{o_total:,} "
                        f"/ お得額¥{savings:,}"
                        + (f"\n{q_memo}" if q_memo else ""))
                append_record({
                    "date": datetime.now().strftime("%Y/%m/%d %H:%M"),
                    "purpose": "タイヤ見積",
                    "cust_type": "", "plate_area": "", "plate_3digit": "", "plate_kana": "",
                    "plate_num": hs_plate, "maker": hs_maker, "car_model": hs_model,
                    "color": "", "age": "", "gender": "",
                    "tire_size": hs_size, "tire_size_num": tire_to_num(hs_size),
                    "tire_year": "", "tire_maker": opt(q_tm), "tire_product": q_tp,
                    "memo": note,
                })
                st.success("見積を保存しました！")
                st.session_state.mode = "list"; st.session_state.searched_plate = hs_plate or ""
                st.session_state.quote_step = "hearing"; st.rerun()

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
        is_dup = st.session_state.get("is_duplicate", False)
        dup    = st.session_state.get("duplicate_data", {})

        if is_dup:
            st.markdown("""
            <div style="background:#fff8e1;border:1.5px solid #ffc107;border-radius:12px;
                        padding:10px 16px;margin-bottom:10px;display:flex;align-items:center;gap:10px">
                <span style="font-size:1.3rem">📋</span>
                <div>
                    <div style="font-size:.9rem;font-weight:800;color:#856404">履歴をコピーして作成中</div>
                    <div style="font-size:.76rem;color:#a07000;margin-top:1px">日時は現在時刻に自動更新されます</div>
                </div>
            </div>""", unsafe_allow_html=True)
            st.markdown("<div class='sec-title'>📋 複製して新規来店記録</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='sec-title'>➕ 新規来店記録</div>", unsafe_allow_html=True)

        def _di(opts, key, fallback=0):
            v = dup.get(key, "") if is_dup else ""
            return sel_idx(opts, v) if v else fallback

        with st.form("new_form"):
            c1,c2,c3 = st.columns(3)
            with c1: f_date    = st.text_input("📅 日付", value=datetime.now().strftime("%Y/%m/%d %H:%M"))
            with c2: f_purpose = st.selectbox("🎯 来店目的", PURPOSE_OPTIONS, index=_di(PURPOSE_OPTIONS, "purpose"))
            with c3: f_ctype   = st.selectbox("👤 種別", CUST_TYPE_OPTIONS, index=_di(CUST_TYPE_OPTIONS, "cust_type"))
            st.markdown("<div class='sec-title'>ナンバープレート</div>", unsafe_allow_html=True)
            p1,p2,p3,p4 = st.columns([2,1,1,1])
            with p1: f_area   = st.selectbox("地名", PLATE_AREAS, index=_di(PLATE_AREAS, "plate_area"))
            with p2: f_3digit = st.text_input("3桁", placeholder="500", max_chars=3, value=dup.get("plate_3digit","") if is_dup else "")
            with p3: f_kana   = st.selectbox("かな", KANA_OPTIONS, index=_di(KANA_OPTIONS, "plate_kana"))
            with p4: f_num    = st.text_input("下4桁", placeholder="1234", max_chars=4, value=dup.get("plate_num","") if is_dup else "")
            st.markdown("<div class='sec-title'>車両情報</div>", unsafe_allow_html=True)
            v1,v2,v3,v4,v5 = st.columns([2,2,2,1,1])
            with v1: f_maker  = st.selectbox("メーカー", MAKER_OPTIONS, index=_di(MAKER_OPTIONS, "maker"))
            with v2: f_car    = st.text_input("車種", placeholder="プリウス", value=dup.get("car_model","") if is_dup else "")
            with v3: f_color  = st.selectbox("カラー", COLOR_OPTIONS, index=_di(COLOR_OPTIONS, "color"))
            with v4: f_age    = st.selectbox("年齢", AGE_OPTIONS, index=_di(AGE_OPTIONS, "age"))
            with v5: f_gender = st.selectbox("性別", GENDER_OPTIONS, index=_di(GENDER_OPTIONS, "gender"))
            st.markdown("<div class='sec-title'>タイヤ情報</div>", unsafe_allow_html=True)
            t1,t2,t3,t4 = st.columns([2,1,2,2])
            with t1: f_tsize  = st.text_input("タイヤサイズ", placeholder="225/50R17", value=dup.get("tire_size","") if is_dup else "")
            with t2: f_tyear  = st.text_input("製造年(下2桁)", placeholder="23", max_chars=2, value=dup.get("tire_year","") if is_dup else "")
            with t3: f_tmaker = st.selectbox("タイヤメーカー", TIRE_MAKER_OPTIONS, index=_di(TIRE_MAKER_OPTIONS, "tire_maker"))
            with t4: f_tprod  = st.text_input("タイヤ商品名", placeholder="ENASAVE EC204", value=dup.get("tire_product","") if is_dup else "")
            f_memo = st.text_area("📝 備考", placeholder="接客メモ・特記事項など", height=80, value=dup.get("memo","") if is_dup else "")
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
            st.success("保存しました！")
            st.session_state.is_duplicate = False; st.session_state.duplicate_data = {}
            st.session_state.mode="list"; st.session_state.searched_plate=""; st.rerun()
        if ng:
            st.session_state.is_duplicate = False; st.session_state.duplicate_data = {}
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

        # 削除完了メッセージ
        if st.session_state.get("deleted_message"):
            st.success(st.session_state.deleted_message)
            st.session_state.deleted_message = ""

        # 削除確認パネル
        del_idx = st.session_state.get("confirm_delete_idx")
        if del_idx is not None and del_idx in df.index:
            crow    = df.loc[del_idx]
            c_plate = " ".join(filter(None,[crow["plate_area"],crow["plate_3digit"],crow["plate_kana"],crow["plate_num"]]))
            c_car   = " ".join(filter(None,[crow["maker"],crow["car_model"]]))
            c_memo  = f'<div style="color:#888;margin-top:4px;font-size:.76rem">{crow["memo"][:60]}</div>' if crow["memo"] else ""
            st.markdown(f"""
            <div style="background:#fff0f0;border:2px solid #ef4444;border-radius:12px;padding:14px 16px;margin:8px 0">
                <div style="font-size:.9rem;font-weight:800;color:#b91c1c;margin-bottom:6px">🗑️ 削除の確認</div>
                <div style="font-size:.82rem;color:#374151;margin-bottom:8px">
                    以下のデータを削除します。この操作は<b>取り消せません</b>。
                </div>
                <div style="background:#fff;border-radius:8px;padding:8px 12px;font-size:.82rem;border:1px solid #fca5a5">
                    <b>{crow['date']}</b>&nbsp;/&nbsp;{crow['purpose']}&nbsp;/&nbsp;{c_plate or '（車番なし）'}&nbsp;/&nbsp;{c_car or '（車種なし）'}
                    {c_memo}
                </div>
            </div>""", unsafe_allow_html=True)
            dc1, dc2, _ = st.columns([1, 1, 4])
            with dc1:
                if st.button("🗑️ はい、削除する", use_container_width=True, key="confirm_delete_btn", type="primary"):
                    new_df = df.drop(index=del_idx)
                    save_history(new_df)
                    label = c_plate or crow["purpose"] or "記録"
                    st.session_state.confirm_delete_idx = None
                    st.session_state.deleted_message = f"「{label}」の記録を削除しました"
                    st.rerun()
            with dc2:
                if st.button("キャンセル", use_container_width=True, key="cancel_delete_btn"):
                    st.session_state.confirm_delete_idx = None
                    st.rerun()

        if filtered.empty:
            st.markdown("<div style='padding:36px;text-align:center;color:#ccc;border:1px dashed #e0e0e0;border-radius:14px;margin-top:10px'>記録が見つかりません</div>", unsafe_allow_html=True)
        else:
            def mk_badge(text: str, cls: str) -> str:
                return f'<span class="badge {cls}">{text}</span>' if text else ""

            # テーブルヘッダー
            hcols = st.columns([1.0,1.0,0.75,1.6,1.6,0.85,1.1,0.95,1.8,0.55,0.55,0.55,0.55])
            for hc, lb in zip(hcols, ["日付","目的","種別","ナンバー","車両","カラー","タイヤ","客層","備考","","編集","複製","削除"]):
                hc.markdown(f"<div style='font-size:.69rem;font-weight:700;color:#aaa;padding-bottom:5px;border-bottom:2px solid #e8e8e8'>{lb}</div>", unsafe_allow_html=True)

            for orig_idx, row in filtered.iterrows():
                plate_str = " ".join(filter(None,[row["plate_area"],row["plate_3digit"],row["plate_kana"],row["plate_num"]]))
                car_str   = " ".join(filter(None,[row["maker"],row["car_model"]]))
                date_s    = str(row["date"])[:16] if row["date"] else ""
                age_s     = row["age"] if row["age"] not in ("","(未選択)") else ""
                gender_b  = mk_badge(row["gender"], f"bg-{row['gender']}")
                purpose_b = mk_badge(row["purpose"], "bp")
                ctype_b   = mk_badge(row["cust_type"], f"bt-{row['cust_type']}")

                rcols = st.columns([1.0,1.0,0.75,1.6,1.6,0.85,1.1,0.95,1.8,0.55,0.55,0.55,0.55])
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
                if rcols[11].button("複製", key=f"dup_{orig_idx}", use_container_width=True):
                    st.session_state.is_duplicate = True
                    st.session_state.duplicate_data = row.to_dict()
                    st.session_state.mode = "new_record"
                    st.session_state.view_idx = None
                    st.rerun()
                if rcols[12].button("🗑️", key=f"del_{orig_idx}", use_container_width=True):
                    st.session_state.confirm_delete_idx = int(orig_idx)
                    st.rerun()

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
