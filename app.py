import streamlit as st
import random
import json
from supabase import create_client, Client

# ── ページ設定 ──────────────────────────────────────────
st.set_page_config(
    page_title="パス単 準1級",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 単語データ ──────────────────────────────────────────
@st.cache_data
def load_words():
    with open("words.json", encoding="utf-8") as f:
        return json.load(f)

WORDS = load_words()

# ── Supabase 接続 ────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()

def load_progress() -> dict:
    """Supabaseから進捗を読み込む"""
    try:
        res = supabase.table("progress").select("word_no, status").execute()
        return {row["word_no"]: row["status"] for row in res.data}
    except Exception:
        return {}

def save_status(word_no: int, status: str):
    """単語の状態をSupabaseに保存（upsert）"""
    try:
        supabase.table("progress").upsert(
            {"word_no": word_no, "status": status},
            on_conflict="word_no"
        ).execute()
    except Exception as e:
        st.warning(f"保存エラー: {e}")

def reset_progress():
    """全進捗を削除"""
    try:
        supabase.table("progress").delete().neq("word_no", 0).execute()
    except Exception as e:
        st.warning(f"リセットエラー: {e}")

# ── Session state 初期化 ─────────────────────────────────
def init_state():
    if "progress" not in st.session_state:
        with st.spinner("進捗を読み込み中..."):
            st.session_state.progress = load_progress()
    if "mode" not in st.session_state:
        st.session_state.mode = "flash"
    if "deck" not in st.session_state:
        st.session_state.deck = []
    if "idx" not in st.session_state:
        st.session_state.idx = 0
    if "flipped" not in st.session_state:
        st.session_state.flipped = False
    if "ja_first" not in st.session_state:
        st.session_state.ja_first = False
    if "range_start" not in st.session_state:
        st.session_state.range_start = 1
    if "range_end" not in st.session_state:
        st.session_state.range_end = 100
    if "filter" not in st.session_state:
        st.session_state.filter = "all"
    if "quiz_deck" not in st.session_state:
        st.session_state.quiz_deck = []
    if "quiz_idx" not in st.session_state:
        st.session_state.quiz_idx = 0
    if "quiz_score" not in st.session_state:
        st.session_state.quiz_score = 0
    if "quiz_selected" not in st.session_state:
        st.session_state.quiz_selected = None
    if "quiz_options" not in st.session_state:
        st.session_state.quiz_options = []
    if "_quiz_card_no" not in st.session_state:
        st.session_state._quiz_card_no = None

init_state()

def build_deck():
    s, e = st.session_state.range_start, st.session_state.range_end
    prog = st.session_state.progress
    filtered = [w for w in WORDS if s <= w["no"] <= e]
    flt = st.session_state.filter
    if flt == "unknown":
        filtered = [w for w in filtered if prog.get(w["no"]) in ("unknown", None)]
    elif flt == "known":
        filtered = [w for w in filtered if prog.get(w["no"]) == "known"]
    st.session_state.deck = filtered
    st.session_state.idx = 0
    st.session_state.flipped = False

if not st.session_state.deck:
    build_deck()

# ── スタイル ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@300;400;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=DM+Mono:wght@300;400&display=swap');

html, body, [class*="css"] {
    background: #0d0d12 !important;
    color: #e8e0d5 !important;
    font-family: 'Noto Serif JP', serif !important;
}
.stApp { background: #0d0d12 !important; }

.flash-card {
    background: linear-gradient(135deg, #1c1c28 0%, #16161f 100%);
    border: 1px solid #2a2a38;
    border-radius: 16px;
    padding: 52px 48px;
    text-align: center;
    margin: 12px 0;
    min-height: 240px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    position: relative;
}
.card-no {
    position: absolute; top: 16px; left: 20px;
    font-family: 'DM Mono', monospace; font-size: 11px;
    color: #7a7a8a; letter-spacing: 1px;
}
.card-label {
    font-family: 'DM Mono', monospace; font-size: 10px;
    color: #c8a96e; letter-spacing: 3px;
    text-transform: uppercase; margin-bottom: 16px; opacity: 0.8;
}
.card-word {
    font-family: 'Playfair Display', serif; font-size: 48px;
    color: #e8e0d5; letter-spacing: 1px; line-height: 1.2; margin: 0;
}
.card-meaning {
    font-size: 28px; color: #e8e0d5;
    line-height: 1.6; font-weight: 300; margin: 0;
}
.card-sub {
    font-family: 'Playfair Display', serif; font-size: 16px;
    color: #c8a96e; margin-top: 12px; font-style: italic;
}
.stat-box {
    background: #16161f; border: 1px solid #2a2a38;
    border-radius: 8px; padding: 12px 16px; text-align: center;
}
.stat-val { font-family: 'Playfair Display', serif; font-size: 28px; }
.stat-label { font-family: 'DM Mono', monospace; font-size: 10px; color: #7a7a8a; margin-top: 2px; }
.prog-wrap { background: #1e1e2a; border-radius: 4px; height: 4px; margin: 8px 0; }
.prog-fill { background: #c8a96e; border-radius: 4px; height: 100%; transition: width 0.4s; }
.word-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 16px; border-bottom: 1px solid #1e1e2a; font-size: 14px;
}
.word-row:hover { background: rgba(200,169,110,0.04); }
.quiz-card {
    background: #1c1c28; border: 1px solid #2a2a38;
    border-radius: 12px; padding: 40px; text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ── ヘッダー ─────────────────────────────────────────────
prog = st.session_state.progress
deck = st.session_state.deck
known_count  = sum(1 for w in deck if prog.get(w["no"]) == "known")
unknown_count = sum(1 for w in deck if prog.get(w["no"]) == "unknown")

c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
with c1:
    st.markdown("""
    <div style='padding:8px 0'>
      <span style='font-family:Playfair Display,serif;font-size:24px;color:#c8a96e'>パス単 準1級</span>
      <span style='font-family:DM Mono,monospace;font-size:12px;color:#7a7a8a;margin-left:12px'>1550語収録</span>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='stat-box'><div class='stat-val'>{len(deck)}</div><div class='stat-label'>今回</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='stat-box'><div class='stat-val' style='color:#5aab7e'>{known_count}</div><div class='stat-label'>覚えた</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='stat-box'><div class='stat-val' style='color:#c06070'>{unknown_count}</div><div class='stat-label'>未習</div></div>", unsafe_allow_html=True)
with c5:
    st.markdown(f"<div class='stat-box'><div class='stat-val' style='color:#7b9cbc'>{len(WORDS)}</div><div class='stat-label'>総単語数</div></div>", unsafe_allow_html=True)

st.markdown("<div style='height:1px;background:#2a2a38;margin:8px 0 16px'></div>", unsafe_allow_html=True)

# ── コントロールバー ──────────────────────────────────────
col_r1, col_r2, col_r3, col_btns = st.columns([1, 1, 1, 3])
with col_r1:
    rs = st.number_input("開始No.", min_value=1, max_value=1550,
                         value=st.session_state.range_start, label_visibility="collapsed")
    st.session_state.range_start = rs
with col_r2:
    re = st.number_input("終了No.", min_value=1, max_value=1550,
                         value=st.session_state.range_end, label_visibility="collapsed")
    st.session_state.range_end = re
with col_r3:
    flt_opt = st.selectbox("フィルター", ["全て", "未習のみ", "覚えたのみ"],
                           index=["all","unknown","known"].index(st.session_state.filter),
                           label_visibility="collapsed")
    st.session_state.filter = {"全て":"all","未習のみ":"unknown","覚えたのみ":"known"}[flt_opt]
with col_btns:
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button("✓ 適用", use_container_width=True):
            build_deck(); st.rerun()
    with b2:
        if st.button("全て", use_container_width=True):
            st.session_state.range_start = 1
            st.session_state.range_end   = 1550
            st.session_state.filter      = "all"
            build_deck(); st.rerun()
    with b3:
        if st.button("🔀 シャッフル", use_container_width=True):
            random.shuffle(st.session_state.deck)
            st.session_state.idx = 0
            st.session_state.flipped = False
            st.rerun()
    with b4:
        label = "🇯🇵→🇬🇧 ON" if st.session_state.ja_first else "🇬🇧→🇯🇵"
        if st.button(label, use_container_width=True):
            st.session_state.ja_first = not st.session_state.ja_first
            st.session_state.flipped  = False
            st.rerun()

st.markdown("<div style='height:1px;background:#2a2a38;margin:8px 0 16px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# タブ
# ══════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs(["📇 フラッシュカード", "📋 一覧", "🎯 クイズ"])

# ─────────────────────────────────────────────────────────
# FLASH CARD
# ─────────────────────────────────────────────────────────
with tab1:
    deck     = st.session_state.deck
    idx      = st.session_state.idx
    flipped  = st.session_state.flipped
    ja_first = st.session_state.ja_first

    if not deck:
        st.warning("条件に一致する単語がありません。")
    elif idx >= len(deck):
        known_n   = sum(1 for w in deck if prog.get(w["no"]) == "known")
        unknown_n = len(deck) - known_n
        st.markdown(f"""
        <div style='text-align:center;padding:60px 20px'>
          <div style='font-family:Playfair Display,serif;font-size:48px;color:#c8a96e;margin-bottom:24px'>完了！</div>
          <div style='display:flex;justify-content:center;gap:48px;margin-bottom:32px'>
            <div><div style='font-size:48px;color:#5aab7e;font-family:Playfair Display,serif'>{known_n}</div><div style='color:#7a7a8a;font-size:12px'>覚えた</div></div>
            <div><div style='font-size:48px;color:#c06070;font-family:Playfair Display,serif'>{unknown_n}</div><div style='color:#7a7a8a;font-size:12px'>未習</div></div>
            <div><div style='font-size:48px;font-family:Playfair Display,serif'>{len(deck)}</div><div style='color:#7a7a8a;font-size:12px'>合計</div></div>
          </div>
        </div>""", unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 もう一度", use_container_width=True):
                st.session_state.idx = 0; st.session_state.flipped = False; st.rerun()
        with col_b:
            if st.button("📚 未習のみ復習", use_container_width=True):
                st.session_state.filter = "unknown"; build_deck(); st.rerun()
    else:
        card   = deck[idx]
        pct    = int(idx / len(deck) * 100)
        status = prog.get(card["no"], "new")
        badge  = {"known":"🟢","unknown":"🔴","new":"⚪"}.get(status,"⚪")

        st.markdown(f"""
        <div style='display:flex;justify-content:space-between;font-family:DM Mono,monospace;font-size:12px;color:#7a7a8a;margin-bottom:4px'>
          <span>{idx+1} / {len(deck)}</span><span>{pct}%</span>
        </div>
        <div class='prog-wrap'><div class='prog-fill' style='width:{pct}%'></div></div>
        """, unsafe_allow_html=True)

        if not flipped:
            word  = card["ja"] if ja_first else card["en"]
            label = "日本語" if ja_first else "英語"
            fsize = "28px" if (ja_first and len(word) > 8) else "48px"
            st.markdown(f"""
            <div class='flash-card'>
              <div class='card-no'>No.{card['no']} {badge}</div>
              <div class='card-label'>{label}</div>
              <div class='card-word' style='font-size:{fsize}'>{word}</div>
              <div style='color:#7a7a8a;font-size:13px;margin-top:20px;font-style:italic'>クリックしてめくる ↓</div>
            </div>""", unsafe_allow_html=True)
        else:
            back  = card["en"] if ja_first else card["ja"]
            front = card["ja"] if ja_first else card["en"]
            label = "英語" if ja_first else "日本語"
            fsize = "24px" if len(back) > 10 else "32px"
            st.markdown(f"""
            <div class='flash-card' style='background:linear-gradient(135deg,#1a1a2e 0%,#16161f 100%);border-color:#3a3a50'>
              <div class='card-no'>No.{card['no']} {badge}</div>
              <div class='card-label'>{label}</div>
              <div class='card-meaning' style='font-size:{fsize}'>{back}</div>
              <div class='card-sub'>{front}</div>
            </div>""", unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
        with col1:
            if st.button("✕ わからない", use_container_width=True):
                save_status(card["no"], "unknown")
                st.session_state.progress[card["no"]] = "unknown"
                st.session_state.idx += 1; st.session_state.flipped = False; st.rerun()
        with col2:
            if st.button("めくる", use_container_width=True):
                st.session_state.flipped = not st.session_state.flipped; st.rerun()
        with col3:
            if st.button("スキップ→", use_container_width=True):
                st.session_state.idx += 1; st.session_state.flipped = False; st.rerun()
        with col4:
            if st.button("○ 覚えた！", use_container_width=True, type="primary"):
                save_status(card["no"], "known")
                st.session_state.progress[card["no"]] = "known"
                st.session_state.idx += 1; st.session_state.flipped = False; st.rerun()

# ─────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────
with tab2:
    search = st.text_input("🔍 検索", placeholder="単語を検索...", label_visibility="collapsed")
    words  = st.session_state.deck
    if search:
        words = [w for w in words if search.lower() in w["en"].lower() or search in w["ja"]]

    st.markdown(f"<div style='font-family:DM Mono,monospace;font-size:12px;color:#7a7a8a;margin-bottom:8px'>{len(words)} 語</div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='display:flex;justify-content:space-between;padding:8px 16px;background:#16161f;border-radius:6px;margin-bottom:4px;font-family:DM Mono,monospace;font-size:11px;color:#7a7a8a'>
      <span>No. 英語</span><span>日本語　状態</span>
    </div>""", unsafe_allow_html=True)

    for w in words[:300]:
        status = prog.get(w["no"], "new")
        badge  = {"known":"🟢","unknown":"🔴","new":"⚪"}.get(status,"⚪")
        st.markdown(f"""
        <div class='word-row'>
          <div><span style='font-family:DM Mono,monospace;font-size:10px;color:#7a7a8a;margin-right:10px'>{w['no']}.</span>
               <span style='font-family:Playfair Display,serif;font-size:16px'>{w['en']}</span></div>
          <div><span style='color:#7a7a8a;font-size:13px'>{w['ja']}</span>
               <span style='margin-left:8px'>{badge}</span></div>
        </div>""", unsafe_allow_html=True)

    if len(words) > 300:
        st.info(f"先頭300語を表示中（全{len(words)}語）。検索で絞り込めます。")

    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    if st.button("⚠️ 全進捗をリセット"):
        reset_progress()
        st.session_state.progress = {}
        st.success("リセットしました！")
        st.rerun()

# ─────────────────────────────────────────────────────────
# QUIZ
# ─────────────────────────────────────────────────────────
with tab3:
    def gen_options(card, ja_first):
        if ja_first:
            correct = card["en"]
            pool    = [w["en"] for w in WORDS if w["no"] != card["no"]]
        else:
            correct = card["ja"]
            pool    = [w["ja"] for w in WORDS if w["no"] != card["no"]]
        random.shuffle(pool)
        opts = [correct] + pool[:3]
        random.shuffle(opts)
        return opts, correct

    if st.button("🎯 クイズを開始 / リスタート", type="primary"):
        qd = st.session_state.deck.copy()
        random.shuffle(qd)
        st.session_state.quiz_deck     = qd
        st.session_state.quiz_idx      = 0
        st.session_state.quiz_score    = 0
        st.session_state.quiz_selected = None
        st.session_state.quiz_options  = []
        st.session_state._quiz_card_no = None
        st.rerun()

    quiz_deck = st.session_state.quiz_deck
    quiz_idx  = st.session_state.quiz_idx
    quiz_score = st.session_state.quiz_score

    if quiz_deck:
        if quiz_idx >= len(quiz_deck):
            pct = int(quiz_score / len(quiz_deck) * 100)
            wrong = len(quiz_deck) - quiz_score
            st.markdown(f"""
            <div style='text-align:center;padding:48px'>
              <div style='font-family:Playfair Display,serif;font-size:40px;color:#c8a96e;margin-bottom:24px'>クイズ完了！</div>
              <div style='display:flex;justify-content:center;gap:40px'>
                <div><div style='font-size:40px;color:#5aab7e;font-family:Playfair Display,serif'>{quiz_score}</div><div style='color:#7a7a8a;font-size:12px'>正解</div></div>
                <div><div style='font-size:40px;color:#c06070;font-family:Playfair Display,serif'>{wrong}</div><div style='color:#7a7a8a;font-size:12px'>不正解</div></div>
                <div><div style='font-size:40px;font-family:Playfair Display,serif'>{pct}%</div><div style='color:#7a7a8a;font-size:12px'>正答率</div></div>
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            card     = quiz_deck[quiz_idx]
            ja_first = st.session_state.ja_first
            qpct     = int(quiz_idx / len(quiz_deck) * 100)

            st.markdown(f"""
            <div style='display:flex;justify-content:space-between;font-family:DM Mono,monospace;font-size:12px;color:#7a7a8a;margin-bottom:4px'>
              <span>{quiz_idx+1} / {len(quiz_deck)}</span><span>正解: {quiz_score}</span>
            </div>
            <div class='prog-wrap'><div class='prog-fill' style='width:{qpct}%'></div></div>
            """, unsafe_allow_html=True)

            if st.session_state._quiz_card_no != card["no"]:
                opts, correct = gen_options(card, ja_first)
                st.session_state.quiz_options  = opts
                st.session_state.quiz_correct  = correct
                st.session_state._quiz_card_no = card["no"]
                st.session_state.quiz_selected = None

            opts     = st.session_state.quiz_options
            correct  = st.session_state.quiz_correct
            selected = st.session_state.quiz_selected

            q_label = "日本語 → 英語" if ja_first else "英語 → 日本語"
            q_word  = card["ja"] if ja_first else card["en"]
            q_size  = "22px" if len(q_word) > 12 else "36px"
            st.markdown(f"""
            <div class='quiz-card'>
              <div style='font-family:DM Mono,monospace;font-size:10px;color:#c8a96e;letter-spacing:2px;margin-bottom:16px'>{q_label}</div>
              <div style='font-family:Playfair Display,serif;font-size:{q_size};color:#e8e0d5'>{q_word}</div>
            </div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            for i, opt in enumerate(opts):
                with (col_a if i % 2 == 0 else col_b):
                    if selected is None:
                        if st.button(opt, key=f"qopt_{quiz_idx}_{i}", use_container_width=True):
                            st.session_state.quiz_selected = opt
                            if opt == correct:
                                st.session_state.quiz_score += 1
                                save_status(card["no"], "known")
                                st.session_state.progress[card["no"]] = "known"
                            else:
                                save_status(card["no"], "unknown")
                                st.session_state.progress[card["no"]] = "unknown"
                            st.rerun()
                    else:
                        if opt == correct:
                            st.success(f"✓ {opt}")
                        elif opt == selected:
                            st.error(f"✗ {opt}")
                        else:
                            st.markdown(f"<div style='padding:8px;border:1px solid #2a2a38;border-radius:6px;text-align:center;color:#7a7a8a;font-size:14px'>{opt}</div>", unsafe_allow_html=True)

            if selected is not None:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                if st.button("次へ →", type="primary", use_container_width=True):
                    st.session_state.quiz_idx     += 1
                    st.session_state.quiz_selected = None
                    st.session_state.quiz_options  = []
                    st.session_state._quiz_card_no = None
                    st.rerun()
