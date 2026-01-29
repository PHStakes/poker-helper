import streamlit as st
import pandas as pd
from treys import Card, Evaluator, Deck

# --- RANGE DEFINITIONS ---
RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
RANGE_DATA = {
    "Raised Pot": ["AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "AKo", "AQo", "AJo", "ATo", "AKs", "AQs", "AJs", "ATs", "KQs", "KJs", "QJs", "JTs"],
    "3-Bet Pot": ["AA", "KK", "QQ", "JJ", "TT", "AKo", "AQo", "AKs", "AQs", "AJs", "KQs"],
    "4-Bet Pot": ["AA", "KK", "QQ", "AKo", "AKs", "AQs"],
    "5-Bet+ Pot": ["AA", "KK", "AKs"]
}

# --- PARSING & AUTO-STREET ENGINE ---
def parse_and_detect_street(raw_input):
    """
    Splits string and detects the street based on card count.
    """
    clean = raw_input.strip().lower().replace("10", "t").replace(" ", "")
    cards = [clean[i:i+2] for i in range(0, len(clean), 2)]
    formatted = [c[0].upper() + c[1].lower() for c in cards if len(c) == 2]
    
    hero_cards = formatted[:2]
    board_cards = formatted[2:]
    
    # Auto-detect street
    count = len(board_cards)
    if count == 0: street = "Pre-flop"
    elif count == 3: street = "Flop"
    elif count == 4: street = "Turn"
    elif count == 5: street = "River"
    else: street = f"Incomplete ({count} board cards)"
    
    return hero_cards, board_cards, street

def get_hand_matrix(pot_type):
    matrix = []
    for i, r1 in enumerate(RANKS):
        row = []
        for j, r2 in enumerate(RANKS):
            if i == j: hand = r1 + r2
            elif i < j: hand = r1 + r2 + "s"
            else: hand = r2 + r1 + "o"
            row.append(hand)
        matrix.append(row)
    return pd.DataFrame(matrix, index=RANKS, columns=RANKS)

# --- ANALYTICS ENGINE ---
def calculate_equity(hero_cards_str, board_cards_str, num_players, sims=1500):
    evaluator = Evaluator()
    wins, ties = 0, 0
    try:
        hero_cards = [Card.new(c) for c in hero_cards_str]
        board_cards = [Card.new(c) for c in board_cards_str]
    except:
        return 0, "Invalid Input"

    for _ in range(sims):
        deck = Deck()
        for c in (hero_cards + board_cards):
            if c in deck.cards: deck.cards.remove(c)
        
        opp_hands = [deck.draw(2) for _ in range(num_players - 1)]
        cards_needed = 5 - len(board_cards)
        full_board = board_cards + (deck.draw(cards_needed) if cards_needed > 0 else [])
        
        hero_score = evaluator.evaluate(hero_cards, full_board)
        best_opp_score = min([evaluator.evaluate(h, full_board) for h in opp_hands])
        
        if hero_score < best_opp_score: wins += 1
        elif hero_score == best_opp_score: ties += 1
            
    curr_label = "N/A"
    if len(hero_cards + board_cards) >= 5:
        curr_label = evaluator.class_to_string(evaluator.get_rank_class(evaluator.evaluate(hero_cards, board_cards[:5])))

    return (wins + (ties * (1/num_players))) / sims * 100, curr_label

# --- UI LAYOUT ---
st.set_page_config(page_title="Auto-Street GTO", layout="wide")
st.title("🚀 Smart Auto-Street Engine")

# --- ONE-LINE INPUT ---
super_string = st.text_input("ENTER CARDS (e.g. askskh4h5c)", help="Hole cards first, then board. No spaces.").lower()
hero_parsed, board_parsed, detected_street = parse_and_detect_street(super_string)

# Visual Confirmation
if hero_parsed:
    st.info(f"📍 **Detected Street:** {detected_street} | **Hand:** {hero_parsed} | **Board:** {board_parsed}")

col_meta, col_pot = st.columns(2)
with col_meta:
    num_players = st.number_input("Players", 2, 9, 2)
    pot_type = st.selectbox("Opponent Range", ["Raised Pot", "3-Bet Pot", "4-Bet Pot", "5-Bet+ Pot"])

with col_pot:
    pot_bb = st.number_input("Total Pot (bb)", 1.0, 1000.0, 10.0)
    action = st.radio("Situation", ["Checked to Me", "Facing a Bet"])
    call_bb = st.number_input("Amount to Call (bb)", 0.0, 1000.0, 5.0) if action == "Facing a Bet" else 0.0

# --- HEATMAP ---
with st.expander("🔥 Range Heatmap", expanded=False):
    def style_range(val):
        color = '#2e7d32' if val in RANGE_DATA[pot_type] else '#1e1e1e'
        return f'background-color: {color}; color: white; border: 1px solid #444;'
    st.table(get_hand_matrix(pot_type).style.applymap(style_range))

# --- ANALYZE ---
if st.button("🔥 RUN GTO ANALYSIS"):
    if len(hero_parsed) < 2:
        st.error("Please enter your cards.")
        st.stop()

    with st.spinner(f"Analyzing {detected_street}..."):
        equity, hand_type = calculate_equity(hero_parsed, board_parsed, num_players)
    
    st.divider()

    # MATH
    pot_odds = (call_bb / (pot_bb + call_bb)) * 100 if call_bb > 0 else 0
    ev = ((equity / 100) * (pot_bb + call_bb)) - ((1 - (equity/100)) * call_bb)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Win Prob", f"{equity:.1f}%")
    m2.metric("Hand Strength", hand_type)
    m3.metric("EV", f"{ev:+.2f} bb")

    # RECOMMENDATION
    st.subheader("💡 Recommendation")
    if action == "Facing a Bet":
        if (equity - pot_odds) > 10:
            st.success(f"## ✅ RAISE")
            msg = f"In a {detected_street} {pot_type}, you have a significant advantage. Raise for value."
        elif equity > pot_odds:
            st.warning("## ✅ CALL")
            msg = f"Your equity ({equity:.1f}%) justifies the price ({pot_odds:.1f}%)."
        else:
            st.error("## ❌ FOLD")
            msg = f"Against a {pot_type} range, your hand is not profitable here."
    else:
        # Texture check for sizing
        is_wet = False
        if board_parsed:
            ranks = sorted([Card.get_rank_int(Card.new(c)) for c in board_parsed])
            is_wet = any(ranks[i+1] - ranks[i] <= 1 for i in range(len(ranks)-1))
        
        if equity > 65:
            size_p = 0.75 if is_wet else 0.33
            st.success(f"## 🟢 VALUE BET: {pot_bb * size_p:.1f}bb ({int(size_p*100)}%)")
            msg = f"Strong {detected_street} hand. {'Charge draws on this wet board.' if is_wet else 'Extract thin value.'}"
        elif equity > 45:
            st.info("## 🟡 CHECK")
            msg = "Good showdown value. Avoid bloating the pot."
        elif is_wet and equity > 25:
            st.warning(f"## 🔵 SEMI-BLUFF: {pot_bb * 0.5:.1f}bb (50%)")
            msg = f"Semi-bluffing the {detected_street} to maximize fold equity."
        else:
            st.error("## ⚪ CHECK / FOLD")
            msg = "No equity. Surrender the pot."

    st.write(f"**Analysis:** {msg}")
