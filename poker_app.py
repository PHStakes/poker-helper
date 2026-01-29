import streamlit as st
import pandas as pd
import numpy as np
from treys import Card, Evaluator, Deck

# --- RANGE DEFINITIONS ---
# Simplified standard ranges for visualization and simulation
RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']

RANGE_DATA = {
    "Raised Pot": ["AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "AKo", "AQo", "AJo", "ATo", "AKs", "AQs", "AJs", "ATs", "KQs", "KJs", "QJs", "JTs"],
    "3-Bet Pot": ["AA", "KK", "QQ", "JJ", "TT", "AKo", "AQo", "AKs", "AQs", "AJs", "KQs"],
    "4-Bet Pot": ["AA", "KK", "QQ", "AKo", "AKs", "AQs"],
    "5-Bet+ Pot": ["AA", "KK", "AKs"]
}

# --- UTILITY: CLEAN INPUTS ---
def clean_card_input(card_str):
    if not card_str: return ""
    clean = card_str.strip().replace(" ", "").replace("10", "T")
    if len(clean) >= 2:
        return clean[0].upper() + clean[1].lower()
    return clean

def get_hand_matrix(pot_type):
    """Generates a 13x13 matrix color-coded by the opponent's range."""
    matrix = []
    active_range = RANGE_DATA[pot_type]
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
def get_hand_label(score):
    if score <= 10: return "Royal Flush"
    if score <= 166: return "Straight Flush"
    if score <= 322: return "Four of a Kind"
    if score <= 1599: return "Full House"
    if score <= 1609: return "Flush"
    if score <= 1620: return "Straight"
    if score <= 2467: return "Three of a Kind"
    if score <= 3325: return "Two Pair"
    if score <= 6185: return "Pair"
    return "High Card"

def analyze_texture(board_strs):
    if not board_strs or len(board_strs) < 3: return "N/A", False
    try:
        cards = [Card.new(clean_card_input(c)) for c in board_strs]
        suits = [Card.get_suit_int(c) for c in cards]
        max_suit = max([suits.count(s) for s in set(suits)])
        ranks = sorted([Card.get_rank_int(c) for c in cards])
        is_connected = any(ranks[i+1] - ranks[i] <= 2 for i in range(len(ranks)-1))
        return ("Wet" if (max_suit >= 2 or is_connected) else "Dry"), (max_suit >= 2 or is_connected)
    except: return "N/A", False

def calculate_equity(hero_hand, board_strs, num_players, pot_type, sims=1500):
    evaluator = Evaluator()
    wins, ties = 0, 0
    try:
        hero_cards = [Card.new(clean_card_input(hero_hand[0])), Card.new(clean_card_input(hero_hand[1]))]
        board_cards = [Card.new(clean_card_input(c)) for c in board_strs if c]
    except: return 0, "Invalid Cards"

    current_strength = "N/A"
    if len(hero_cards + board_cards) >= 5:
        current_strength = get_hand_label(evaluator.evaluate(hero_cards, board_cards[:5]))

    for _ in range(sims):
        deck = Deck()
        for c in (hero_cards + board_cards): deck.cards.remove(c)
        opp_hands = [deck.draw(2) for _ in range(num_players - 1)]
        cards_needed = 5 - len(board_cards)
        full_board = board_cards + (deck.draw(cards_needed) if cards_needed > 0 else [])
        hero_score = evaluator.evaluate(hero_cards, full_board)
        best_opp_score = min([evaluator.evaluate(h, full_board) for h in opp_hands])
        if hero_score < best_opp_score: wins += 1
        elif hero_score == best_opp_score: ties += 1
    return (wins + (ties * (1/num_players))) / sims * 100, current_strength

# --- UI ---
st.set_page_config(page_title="Pro GTO Engine", layout="wide")
st.title("🃏 Pro GTO Heatmap Engine (bb)")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Situation Context")
    c_st, c_pl, c_pt = st.columns(3)
    street = c_st.selectbox("Street", ["Pre-flop", "Flop", "Turn", "River"])
    num_players = c_pl.number_input("Players", 2, 9, 2)
    pot_type = c_pt.selectbox("Pot Type", ["Raised Pot", "3-Bet Pot", "4-Bet Pot", "5-Bet+ Pot"])
    
    c1, c2 = st.columns(2)
    h1 = c1.text_input("Hole Card 1", "").lower()
    h2 = c2.text_input("Hole Card 2", "").lower()
    
    board_list = []
    if street != "Pre-flop":
        board_input = st.text_input("Board (e.g. 10h 7d 2s)", "").lower()
        board_list = board_input.split()

with col2:
    st.subheader("2. Action & Pot")
    pot_bb = st.number_input("Total Pot (bb)", 1.0, 1000.0, 10.0)
    action = st.radio("Action", ["Checked to Me / I Act First", "Facing a Bet"])
    call_bb = st.number_input("Amount to Call (bb)", 0.0, 1000.0, 5.0) if action == "Facing a Bet" else 0.0

# --- HEATMAP DISPLAY ---
st.divider()
st.subheader(f"🔥 Opponent Range Heatmap: {pot_type}")

def style_range(val):
    color = '#2e7d32' if val in RANGE_DATA[pot_type] else '#1e1e1e'
    return f'background-color: {color}; color: white; border: 1px solid #444;'

df_range = get_hand_matrix(pot_type)
st.table(df_range.style.applymap(style_range))


# --- EXECUTION ---
if st.button("RUN GTO ANALYSIS"):
    if not h1 or not h2: st.error("Enter hole cards."); st.stop()
    with st.spinner("Calculating Game Theory..."):
        equity, hand_type = calculate_equity([h1, h2], board_list, num_players, pot_type)
    
    st.divider()
    
    # MATH PANEL
    pot_odds = (call_bb / (pot_bb + call_bb)) * 100 if call_bb > 0 else 0
    ev = ((equity / 100) * (pot_bb + call_bb)) - ((1 - (equity/100)) * call_bb)
    alpha = (0.75 / (1 + 0.75)) * 100 # Standard alpha for 75% pot bet
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Hand Equity", f"{equity:.1f}%")
    m2.metric("Pot Odds", f"{pot_odds:.1f}%")
    m3.metric("Exp. Value (EV)", f"{ev:+.2f} bb")
    m4.metric("Fold Equity Req.", f"{alpha:.0f}%" if action != "Facing a Bet" else "N/A")

    # RECOMMENDATION
    texture, is_wet = analyze_texture(board_list)
    if action == "Facing a Bet":
        diff = equity - pot_odds
        if diff > 10: rec, color, msg = "✅ RAISE", "success", "You are crushing the opponent's range."
        elif diff > 0: rec, color, msg = "✅ CALL", "warning", f"Profitable call (+{ev:.1f}bb EV)."
        else: rec, color, msg = "❌ FOLD", "error", f"Negative EV ({ev:.1f}bb). Their range is too strong."
    else:
        if equity > 60:
            size = 0.75 if is_wet else 0.33
            rec, color, msg = f"🟢 VALUE BET: {pot_bb*size:.1f}bb ({int(size*100)}% Pot)", "success", "Extracting value from their range."
        elif is_wet and 25 < equity < 45:
            rec, color, msg = f"🔵 SEMI-BLUFF: {pot_bb*0.5:.1f}bb (50% Pot)", "warning", "High fold equity on this wet board."
        else: rec, color, msg = "🟡 CHECK", "info", "Control the pot and take a free card."

    st.markdown(f"{getattr(st, color)}(f'## {rec}')")
    st.write(f"**Summary:** {msg}")
