import streamlit as st
import pandas as pd
from treys import Card, Evaluator, Deck

# --- UPDATED POSITION LOOKUP ---
POS_LOOKUP = {
    'ug': 'UTG', 'ep': 'EP', 'mp': 'MP', 'lj': 'LJ', 
    'hj': 'HJ', 'co': 'CO', 'bn': 'BTN', 'sb': 'SB', 'bb': 'BB'
}

# --- IMPROVED CARD PARSER (Fixes KeyError '1' and 't') ---
def parse_cards(raw_input):
    # Converts '10' to 'T' and forces uppercase for the rank
    clean = raw_input.strip().lower().replace("10", "t").replace(" ", "")
    cards = [clean[i:i+2] for i in range(0, len(clean), 2)]
    
    formatted = []
    for c in cards:
        if len(c) == 2:
            rank = c[0].upper() # Fixes lowercase 't' issue
            suit = c[1].lower()
            formatted.append(f"{rank}{suit}")
            
    hero = formatted[:2]
    board = formatted[2:]
    return hero, board

# --- SIMULATION ENGINE (Fixes NameError 'o_score') ---
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
        
        # FIXED: Use consistent variable names to avoid NameError
        h_score = evaluator.evaluate(hero_cards, full_board)
        opp_scores = [evaluator.evaluate(opp, full_board) for opp in opp_hands]
        best_opp_score = min(opp_scores) if opp_scores else 9999
        
        if h_score < best_opp_score: wins += 1
        elif h_score == best_opp_score: ties += 1
            
    hand_label = "High Card"
    if len(hero_cards + board_cards) >= 5:
        hand_label = evaluator.class_to_string(evaluator.get_rank_class(evaluator.evaluate(hero_cards, board_cards[:5])))
    
    return (wins + (ties * (1/(num_opps+1)))) / sims * 100, hand_label

# --- UI ---
st.set_page_config(page_title="Stakked Poker", layout="wide")
st.title("🃏 Stakked Poker")

st.subheader("⚡ Quick Entry")
c1, c2 = st.columns(2)
with c1:
    act_string = st.text_input("ACTION (e.g., 9bnffffff)", placeholder="[Size][Pos][Actions]").lower()
with c2:
    card_string = st.text_input("CARDS (e.g., asks7h8c2d)", placeholder="Hole+Board").lower()

pot_bb = st.number_input("Pot Size (bb)", 1.0, 2000.0, 15.0)
status = st.radio("Status", ["Checked to Me", "Facing a Bet"])
call_bb = st.number_input("To Call (bb)", 0.0, 1000.0, 5.0) if status == "Facing a Bet" else 0.0

if st.button("🔥 RUN GTO ANALYSIS"):
    # Basic Parsing
    hero_p, board_p = parse_cards(card_string)
    num_opps = 1 # Default to 1 if action string is empty
    
    if act_string and len(act_string) > 3:
        actions = act_string[3:]
        num_opps = max(1, len([a for a in actions if a != 'f']) - 1)

    with st.spinner("Calculating..."):
        equity, hand_type = calculate_equity(hero_p, board_p, num_opps)
    
    st.divider()
    
    # MATH RESULTS
    odds = (call_bb / (pot_bb + call_bb)) * 100 if call_bb > 0 else 0
    ev = ((equity / 100) * (pot_bb + call_bb)) - ((1 - (equity/100)) * call_bb)
    
    res1, res2, res3 = st.columns(3)
    res1.metric("Win Prob", f"{equity:.1f}%")
    res2.metric("Hand Type", hand_type)
    res3.metric("EV", f"{ev:+.2f} bb")

    # --- NEW BET SIZING & RECOMMENDATION LOGIC ---
    st.subheader("💡 Recommendation & Sizing")
    if status == "Facing a Bet":
        diff = equity - odds
        if diff > 10: st.success("## ✅ RAISE (3x)"); msg = "Massive equity edge. Re-raise for value."
        elif diff > 0: st.warning("## ✅ CALL"); msg = "Pot odds justify a call."
        else: st.error("## ❌ FOLD"); msg = "Equity is too low for this price."
    else:
        if equity > 70: 
            st.success("## 🟢 BET LARGE (75% Pot)")
            msg = f"Strong {hand_type}. Build the pot now."
        elif equity > 45: 
            st.success("## 🟢 BET SMALL (33% Pot)")
            msg = "Standard range bet to deny equity."
        elif equity > 30: 
            st.info("## 🟡 CHECK")
            msg = "Showdown value. Keep the pot small."
        else: 
            st.error("## ⚪ CHECK / FOLD")
            msg = "Too weak to continue."
    
    st.write(f"**Analysis:** {msg}")
