import streamlit as st
import pandas as pd
import numpy as np
import os
from treys import Card, Evaluator, Deck
from datetime import datetime

# --- AUTOMATIC VERSIONING LOGIC ---
def get_app_info():
    start_date = datetime(2026, 1, 29)
    days_since = (datetime.now() - start_date).days
    auto_version = 1.01 + (max(0, days_since) * 0.01)
    try:
        mod_time = os.path.getmtime(__file__)
        last_updated = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
    except:
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"{auto_version:.2f}", last_updated

VERSION, UPDATED_TIME = get_app_info()

# --- LOGIC ENGINES ---
def parse_cards(raw_input):
    clean = raw_input.strip().lower().replace("10", "t").replace(" ", "")
    cards = [clean[i:i+2] for i in range(0, len(clean), 2)]
    formatted = []
    for c in cards:
        if len(c) == 2:
            formatted.append(f"{c[0].upper()}{c[1].lower()}")
    return formatted[:2], formatted[2:]

def get_opponents_from_streets(pre, flop, turn, river):
    """Calculates active opponents based on the latest street action."""
    # Start with the latest non-empty action string
    for action in [river, turn, flop, pre]:
        if action and len(action) > 3:
            # Count everyone who didn't fold ('f') minus the hero
            active = len([a for a in action[3:] if a != 'f']) - 1
            return max(1, active)
    return 1

def calculate_equity(hero_str, board_str, num_opps, sims=1000):
    evaluator = Evaluator()
    wins, ties = 0, 0
    try:
        hero_cards = [Card.new(c) for c in hero_str]
        board_cards = [Card.new(c) for c in board_str]
    except: return 0, "Input Error"

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
            
    combined = hero_cards + board_cards
    if len(combined) >= 5:
        score = evaluator.evaluate(hero_cards, board_cards[:min(5, len(board_cards))])
        hand_label = evaluator.class_to_string(evaluator.get_rank_class(score))
    else: hand_label = "High Card"
    
    return (wins + (ties * (1/(num_opps+1)))) / sims * 100, hand_label

def get_pro_heatmap():
    ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    grid = pd.DataFrame("", index=ranks, columns=ranks)
    color_map = np.zeros((13, 13))
    for i, r1 in enumerate(ranks):
        for j, r2 in enumerate(ranks):
            if i == j: 
                grid.iloc[i, j] = f"{r1}{r2}"
                color_map[i, j] = 0.95 - (i * 0.06)
            elif i < j: 
                grid.iloc[i, j] = f"{r1}{r2}s"
                color_map[i, j] = 0.75 - (i * 0.05)
            else: 
                grid.iloc[i, j] = f"{r2}{r1}o"
                color_map[i, j] = 0.45 - (j * 0.04)
    return grid.style.background_gradient(cmap='RdYlGn', axis=None, gmap=color_map)\
        .set_properties(**{'text-align': 'center', 'font-size': '11px', 'height': '32px'})

# --- UI ---
st.set_page_config(page_title="Stakked Poker", layout="wide")
st.title("🃏 Stakked Poker")

# --- STREET ACTION INPUTS ---
st.subheader("🧬 Hand Action by Street")
col_a, col_b, col_c, col_d = st.columns(4)
pre_action = col_a.text_input("Pre-Flop (e.g. 6bnffrfff)", key="pre").lower()
flop_action = col_b.text_input("Flop Action", key="flop").lower()
turn_action = col_c.text_input("Turn Action", key="turn").lower()
river_action = col_d.text_input("River Action", key="river").lower()

st.divider()

c1, c2 = st.columns(2)
with c1: 
    card_string = st.text_input("CARDS (Hole + Board)", placeholder="asadkhqcjs").lower()
with c2:
    status = st.radio("Current Situation", ["Checked to Me", "Facing a Bet"], horizontal=True)

p_col1, p_col2 = st.columns(2)
pot_bb = p_col1.number_input("Total Pot (bb)", 1.0, 1000.0, 15.0)
call_bb = p_col2.number_input("To Call (bb)", 0.0, 500.0, 5.0) if status == "Facing a Bet" else 0.0

if st.button("🔥 RUN GTO ANALYSIS"):
    hero_p, board_p = parse_cards(card_string)
    num_opps = get_opponents_from_streets(pre_action, flop_action, turn_action, river_action)
    
    with st.spinner(f"Simulating vs {num_opps} Opponents..."):
        equity, hand_type = calculate_equity(hero_p, board_p, num_opps)
    
    st.divider()
    
    # Results
    m1, m2, m3 = st.columns(3)
    m1.metric("Win Prob", f"{equity:.1f}%")
    m2.metric("Hand Strength", hand_type) 
    ev = ((equity/100)*pot_bb) - ((1-(equity/100))*call_bb)
    m3.metric("EV", f"{ev:+.2f} bb")

    st.subheader("📊 Opponent Range Matrix")
    st.markdown("*Top-Right: Suited | Bottom-Left: Offsuit | Diagonal: Pairs*")
    
    st.table(get_pro_heatmap())

    # Recommendation & Summary
    st.subheader("💡 Recommendation")
    if status == "Facing a Bet":
        odds = (call_bb / (pot_bb + call_bb)) * 100
        if equity > odds + 15: st.success("## ✅ RAISE"); decision = "Raise"
        elif equity > odds: st.warning("## ✅ CALL"); decision = "Call"
        else: st.error("## ❌ FOLD"); decision = "Fold"
    else:
        if equity > 65: st.success("## 🟢 VALUE BET (75%)"); decision = "Bet (Value)"
        elif equity > 45: st.success("## 🟢 C-BET (33%)"); decision = "Bet (Denial)"
        else: st.info("## 🟡 CHECK"); decision = "Check"

    st.subheader("📝 Analysis Summary")
    s1, s2 = st.columns(2)
    with s1:
        st.write(f"**Hand:** {hand_type}")
        st.write(f"**Opponents:** Tracking {num_opps} player(s) through streets.")
    with s2:
        if status == "Facing a Bet":
            st.write(f"**Math:** Pot Odds require **{odds:.1f}%**. You have **{equity:.1f}%**.")
        st.write(f"**Verdict:** {decision} is the most profitable play.")

# --- AUTO-STAMP ---
st.markdown(f"<br><hr><center><p style='color: gray; font-size: 10px;'>v{VERSION} | Live Since: {UPDATED_TIME}</p></center>", unsafe_allow_html=True)
