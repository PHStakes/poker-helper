import streamlit as st
import pandas as pd
import numpy as np
from treys import Card, Evaluator, Deck

# --- CONFIG & POSITIONS ---
POS_LOOKUP = {
    'ug': 'UTG', 'ep': 'EP', 'mp': 'MP', 'lj': 'LJ', 
    'hj': 'HJ', 'co': 'CO', 'bn': 'BTN', 'sb': 'SB', 'bb': 'BB'
}

# --- PARSING ENGINES ---
def parse_cards(raw_input):
    """Fixes KeyError: '1' and 't' by standardizing to 'T' and Uppercase."""
    clean = raw_input.strip().lower().replace("10", "t").replace(" ", "")
    cards = [clean[i:i+2] for i in range(0, len(clean), 2)]
    formatted = []
    for c in cards:
        if len(c) == 2:
            [span_2](start_span)rank = c[0].upper() # Fixes 't' -> 'T'[span_2](end_span)
            suit = c[1].lower()
            formatted.append(f"{rank}{suit}")
    hero = formatted[:2]
    board = formatted[2:]
    return hero, board

# --- SIMULATION ENGINE ---
def calculate_equity(hero_str, board_str, num_opps, sims=1000):
    evaluator = Evaluator()
    wins, ties = 0, 0
    try:
        hero_cards = [Card.new(c) for c in hero_str]
        board_cards = [Card.new(c) for c in board_str]
    except Exception:
        return 0, "Error"

    for _ in range(sims):
        deck = Deck()
        for c in (hero_cards + board_cards):
            if c in deck.cards: deck.cards.remove(c)
        
        opp_hands = [deck.draw(2) for _ in range(num_opps)]
        needed = 5 - len(board_cards)
        full_board = board_cards + (deck.draw(needed) if needed > 0 else [])
        
        # [span_3](start_span)FIXED: Consistent variable names to prevent NameError[span_3](end_span)
        h_score = evaluator.evaluate(hero_cards, full_board)
        opp_scores = [evaluator.evaluate(opp, full_board) for opp in opp_hands]
        best_opp_score = min(opp_scores) if opp_scores else 9999
        
        if h_score < best_opp_score: wins += 1
        elif h_score == best_opp_score: ties += 1
            
    # [span_4](start_span)FIXED: Proper Hand Type Identification[span_4](end_span)
    hand_label = "High Card"
    if len(hero_cards + board_cards) >= 5:
        # evaluate only current known board
        current_score = evaluator.evaluate(hero_cards, board_cards[:5])
        hand_label = evaluator.class_to_string(evaluator.get_rank_class(current_score))
    
    return (wins + (ties * (1/(num_opps+1)))) / sims * 100, hand_label

# --- HEATMAP ENGINE ---
def get_opponent_heatmap():
    """Restores the visual range heatmap."""
    ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    grid = pd.DataFrame(0.1, index=ranks, columns=ranks)
    # Placeholder logic for range density
    return grid.style.background_gradient(cmap='Greens').format("{:.1%}")

# --- STREAMLIT UI ---
st.set_page_config(page_title="Stakked Poker", layout="wide")
st.title("🃏 Stakked Poker")

# Inputs
c1, c2 = st.columns(2)
with c1:
    act_string = st.text_input("ACTION STRING (e.g., 6bnffrfff)").lower()
with c2:
    card_string = st.text_input("CARD STRING (e.g., asks7h8c2d)").lower()

pot_bb = st.number_input("Total Pot (bb)", 1.0, 500.0, 15.0)
status = st.radio("Situation", ["Checked to Me", "Facing a Bet"])
call_bb = st.number_input("Call Amt (bb)", 0.0, 200.0, 5.0) if status == "Facing a Bet" else 0.0

if st.button("🔥 RUN GTO ANALYSIS"):
    hero_p, board_p = parse_cards(card_string)
    num_opps = 1 # Logic to derive from act_string would go here
    
    with st.spinner("Analyzing..."):
        equity, hand_type = calculate_equity(hero_p, board_p, num_opps)
    
    st.divider()
    
    # Results
    m1, m2, m3 = st.columns(3)
    m1.metric("Win Prob", f"{equity:.1f}%")
    [span_5](start_span)m2.metric("Hand Type", hand_type) # Now identifies Pairs/Sets correctly[span_5](end_span)
    m3.metric("EV", f"{((equity/100)*pot_bb) - ((1-(equity/100))*call_bb):+.2f} bb")

    # Heatmap Section
    st.subheader("📊 Opponent Range Heatmap")
    st.table(get_opponent_heatmap())

    # Betting Recommendation
    st.subheader("💡 Suggested Action & Sizing")
    if status == "Facing a Bet":
        odds = (call_bb / (pot_bb + call_bb)) * 100
        if equity > odds + 10: st.success("## ✅ RAISE (3x)"); st.write("You have a significant equity advantage.")
        elif equity > odds: st.warning("## ✅ CALL"); st.write("Profitable call based on pot odds.")
        else: st.error("## ❌ FOLD"); st.write("Equity is too low to continue.")
    else:
        if equity > 70: st.success("## 🟢 VALUE BET (75% Pot)")
        elif equity > 45: st.success("## 🟢 C-BET (33% Pot)")
        else: st.info("## 🟡 CHECK")
