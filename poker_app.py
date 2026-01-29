import streamlit as st
import pandas as pd
import numpy as np
from treys import Card, Evaluator, Deck

# --- CONFIG ---
POS_LOOKUP = {'ug':'UTG','ep':'EP','mp':'MP','lj':'LJ','hj':'HJ','co':'CO','bn':'BTN','sb':'SB','bb':'BB'}

def parse_cards(raw_input):
    clean = raw_input.strip().lower().replace("10", "t").replace(" ", "")
    cards = [clean[i:i+2] for i in range(0, len(clean), 2)]
    formatted = []
    for c in cards:
        if len(c) == 2:
            formatted.append(f"{c[0].upper()}{c[1].lower()}")
    return formatted[:2], formatted[2:]

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
            
    # Evaluation for Hand Type
    combined = hero_cards + board_cards
    if len(combined) >= 5:
        score = evaluator.evaluate(hero_cards, board_cards[:min(5, len(board_cards))])
        hand_label = evaluator.class_to_string(evaluator.get_rank_class(score))
    else: hand_label = "High Card"
    
    return (wins + (ties * (1/(num_opps+1)))) / sims * 100, hand_label

def get_pro_heatmap():
    """Generates a standard 169-hand poker grid with suited/offsuit labels."""
    ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    grid = pd.DataFrame("", index=ranks, columns=ranks)
    data = np.zeros((13, 13))

    for i, r1 in enumerate(ranks):
        for j, r2 in enumerate(ranks):
            if i == j: # Pairs
                grid.iloc[i, j] = f"{r1}{r2}"
                data[i, j] = 0.8 - (i * 0.05) # Stronger colors for high pairs
            elif i < j: # Suited
                grid.iloc[i, j] = f"{r1}{r2}s"
                data[i, j] = 0.6 - (i * 0.04)
            else: # Offsuit
                grid.iloc[i, j] = f"{r2}{r1}o"
                data[i, j] = 0.4 - (j * 0.03)
    
    return grid.style.background_gradient(cmap='RdYlGn', axis=None, gnumeric=data).set_properties(**{'text-align': 'center', 'padding': '10px'})

# --- UI ---
st.set_page_config(page_title="Stakked Poker", layout="wide")
st.title("🃏 Stakked Poker")

c1, c2 = st.columns(2)
with c1: act_string = st.text_input("ACTION STRING (e.g., 6bnffrfff)").lower()
with c2: card_string = st.text_input("CARD STRING (e.g., asadkhqcjs)").lower()

pot_bb = st.number_input("Total Pot (bb)", 1.0, 1000.0, 15.0)
status = st.radio("Situation", ["Checked to Me", "Facing a Bet"])
call_bb = st.number_input("To Call (bb)", 0.0, 500.0, 5.0) if status == "Facing a Bet" else 0.0

if st.button("🔥 RUN GTO ANALYSIS"):
    hero_p, board_p = parse_cards(card_string)
    num_opps = max(1, len([a for a in act_string[3:] if a != 'f']) - 1) if len(act_string) > 3 else 1
    
    with st.spinner("Analyzing Hand..."):
        equity, hand_type = calculate_equity(hero_p, board_p, num_opps)
    
    st.divider()
    
    # Results Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Win Prob", f"{equity:.1f}%")
    m2.metric("Hand Strength", hand_type) 
    ev = ((equity/100)*pot_bb) - ((1-(equity/100))*call_bb)
    m3.metric("EV", f"{ev:+.2f} bb")

    # The New 169-Hand Heatmap
    st.subheader("📊 Opponent Range Matrix")
    st.write("Top-Right: Suited | Bottom-Left: Offsuit | Diagonal: Pairs")
    st.table(get_pro_heatmap())

    # Decision Recommendation
    st.subheader("💡 Recommendation")
    if status == "Facing a Bet":
        odds = (call_bb / (pot_bb + call_bb)) * 100
        if equity > odds + 15: st.success("## ✅ RAISE (Value)"); decision = "Raise"
        elif equity > odds: st.warning("## ✅ CALL (Pot Odds)"); decision = "Call"
        else: st.error("## ❌ FOLD"); decision = "Fold"
    else:
        if equity > 65: st.success("## 🟢 VALUE BET (75%)"); decision = "Bet (Value)"
        elif equity > 45: st.success("## 🟢 C-BET (33%)"); decision = "Bet (Denial)"
        else: st.info("## 🟡 CHECK"); decision = "Check"

    # Restoration of Explanation Summary
    st.subheader("📝 Analysis Summary")
    summary_col1, summary_col2 = st.columns(2)
    with summary_col1:
        st.write(f"**Current Holding:** Your hole cards make a **{hand_type}** on this board.")
        st.write(f"**Field Strength:** You are playing against **{num_opps}** active opponent(s).")
    with summary_col2:
        if status == "Facing a Bet":
            st.write(f"**Pot Odds:** You need **{odds:.1f}%** equity to break even on a call.")
            st.write(f"**Edge:** You have a **{equity - odds:+.1f}%** margin over the required odds.")
        st.write(f"**Strategic Goal:** {decision} is the mathematically superior move to maximize long-term EV.")

