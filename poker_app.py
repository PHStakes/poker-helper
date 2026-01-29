import streamlit as st
import pandas as pd
import numpy as np
from treys import Card, Evaluator, Deck

# --- CONFIG & POSITIONS ---
POS_LOOKUP = {
    'ug': 'UTG', 'ep': 'EP', 'mp': 'MP', 'lj': 'LJ', 
    'hj': 'HJ', 'co': 'CO', 'bn': 'BTN', 'sb': 'SB', 'bb': 'BB'
}

def parse_cards(raw_input):
    """Standardizes card ranks to prevent KeyError: '1' or 't'."""
    clean = raw_input.strip().lower().replace("10", "t").replace(" ", "")
    cards = [clean[i:i+2] for i in range(0, len(clean), 2)]
    formatted = []
    for c in cards:
        if len(c) == 2:
            rank = c[0].upper()
            suit = c[1].lower()
            formatted.append(f"{rank}{suit}")
    hero = formatted[:2]
    board = formatted[2:]
    return hero, board

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
        
        h_score = evaluator.evaluate(hero_cards, full_board)
        opp_scores = [evaluator.evaluate(opp, full_board) for opp in opp_hands]
        best_opp_score = min(opp_scores) if opp_scores else 9999
        
        if h_score < best_opp_score: wins += 1
        elif h_score == best_opp_score: ties += 1
            
    hand_label = "High Card"
    if len(hero_cards) == 2 and len(board_cards) >= 3:
        # Evaluate current hand strength based on the cards visible
        hand_score = evaluator.evaluate(hero_cards, board_cards[:min(5, len(board_cards))])
        hand_label = evaluator.class_to_string(evaluator.get_rank_class(hand_score))
    
    return (wins + (ties * (1/(num_opps+1)))) / sims * 100, hand_label

def get_opponent_heatmap():
    """Generates a range heatmap. Safely handles missing matplotlib."""
    ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    grid = pd.DataFrame(0.1, index=ranks, columns=ranks)
    try:
        return grid.style.background_gradient(cmap='Greens').format("{:.1%}")
    except ImportError:
        # Fallback if matplotlib isn't loaded yet
        return grid.style.format("{:.1%}")

# --- STREAMLIT UI ---
st.set_page_config(page_title="Stakked Poker", layout="wide")
st.title("🃏 Stakked Poker")

c1, c2 = st.columns(2)
with c1:
    act_string = st.text_input("ACTION STRING (e.g., 9bnffffff)").lower()
with c2:
    card_string = st.text_input("CARD STRING (e.g., asks7h8c2d)").lower()

pot_bb = st.number_input("Total Pot (bb)", 1.0, 500.0, 15.0)
status = st.radio("Situation", ["Checked to Me", "Facing a Bet"])
call_bb = st.number_input("Call Amt (bb)", 0.0, 200.0, 5.0) if status == "Facing a Bet" else 0.0

if st.button("🔥 RUN GTO ANALYSIS"):
    hero_p, board_p = parse_cards(card_string)
    
    num_opps = 1
    if act_string and len(act_string) > 3:
        actions = act_string[3:]
        num_opps = max(1, len([a for a in actions if a != 'f']) - 1)

    with st.spinner("Analyzing..."):
        equity, hand_type = calculate_equity(hero_p, board_p, num_opps)
    
    st.divider()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Win Prob", f"{equity:.1f}%")
    m2.metric("Hand Type", hand_type) 
    m3.metric("EV", f"{((equity/100)*pot_bb) - ((1-(equity/100))*call_bb):+.2f} bb")

    st.subheader("📊 Opponent Range Heatmap")
    st.table(get_opponent_heatmap())

    st.subheader("💡 Suggested Action & Sizing")
    if status == "Facing a Bet":
        odds = (call_bb / (pot_bb + call_bb)) * 100
        if equity > odds + 10: st.success("## ✅ RAISE (3x)")
        elif equity > odds: st.warning("## ✅ CALL")
        else: st.error("## ❌ FOLD")
    else:
        if equity > 70: st.success("## 🟢 VALUE BET (75% Pot)")
        elif equity > 45: st.success("## 🟢 C-BET (33% Pot)")
        else: st.info("## 🟡 CHECK")
