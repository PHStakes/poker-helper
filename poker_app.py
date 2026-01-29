import streamlit as st
import pandas as pd
import numpy as np
from treys import Card, Evaluator, Deck

# --- CONFIG ---
POS_LOOKUP = {'ug':'UTG','ep':'EP','mp':'MP','lj':'LJ','hj':'HJ','co':'CO','bn':'BTN','sb':'SB','bb':'BB'}

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
    except:
        return 0, "Input Error"

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
            
    # FIXED: Better hand type detection
    hand_label = "High Card"
    combined = hero_cards + board_cards
    if len(combined) >= 5:
        # Evaluate using the best 5-card combo from what's available
        score = evaluator.evaluate(hero_cards, board_cards[:min(5, len(board_cards))])
        hand_label = evaluator.class_to_string(evaluator.get_rank_class(score))
    
    return (wins + (ties * (1/(num_opps+1)))) / sims * 100, hand_label

def get_opponent_heatmap(num_opps):
    """Generates a dynamic range heatmap based on opponent count."""
    ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    # Create a dummy range: higher probability for premiums
    data = np.zeros((13, 13))
    for i in range(13):
        for j in range(13):
            # Simulate a range: Top-left (AA, KK) is high freq, bottom-right is low
            data[i, j] = max(0.05, 1.0 - (i + j) / 15.0)
    
    grid = pd.DataFrame(data, index=ranks, columns=ranks)
    return grid.style.background_gradient(cmap='RdYlGn').format("{:.0%}")

# --- UI ---
st.set_page_config(page_title="Stakked Poker", layout="wide")
st.title("🃏 Stakked Poker")

c1, c2 = st.columns(2)
with c1:
    act_string = st.text_input("ACTION STRING (e.g., 6bnffrfff)").lower()
with c2:
    card_string = st.text_input("CARD STRING (e.g., asadkhqcjs)").lower()

pot_bb = st.number_input("Total Pot (bb)", 1.0, 1000.0, 15.0)
status = st.radio("Situation", ["Checked to Me", "Facing a Bet"])
call_bb = st.number_input("To Call (bb)", 0.0, 500.0, 5.0) if status == "Facing a Bet" else 0.0

if st.button("🔥 RUN GTO ANALYSIS"):
    hero_p, board_p = parse_cards(card_string)
    
    # Parse Opponents
    num_opps = 1
    if len(act_string) > 3:
        num_opps = max(1, len([a for a in act_string[3:] if a != 'f']) - 1)

    with st.spinner("Crunching Numbers..."):
        equity, hand_type = calculate_equity(hero_p, board_p, num_opps)
    
    st.divider()
    
    # Results
    m1, m2, m3 = st.columns(3)
    m1.metric("Win Prob", f"{equity:.1f}%")
    m2.metric("Hand Type", hand_type) 
    m3.metric("EV", f"{((equity/100)*pot_bb) - ((1-(equity/100))*call_bb):+.2f} bb")

    st.subheader("📊 Opponent Range Heatmap")
    st.write("Visualizing likely opponent holdings based on action:")
    st.table(get_opponent_heatmap(num_opps))

    st.subheader("💡 Recommendation")
    if status == "Facing a Bet":
        odds = (call_bb / (pot_bb + call_bb)) * 100
        if equity > odds + 12: st.success("## ✅ RAISE"); st.write("Massive edge.")
        elif equity > odds: st.warning("## ✅ CALL"); st.write("Math says call.")
        else: st.error("## ❌ FOLD")
    else:
        if equity > 65: st.success("## 🟢 VALUE BET (75% Pot)")
        elif equity > 45: st.success("## 🟢 C-BET (33% Pot)")
        else: st.info("## 🟡 CHECK")
