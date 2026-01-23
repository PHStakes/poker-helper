import streamlit as st
import random
from treys import Card, Evaluator, Deck

# --- ENGINE ---
def get_hand_label(score):
    """Converts Treys score to human-readable hand rank."""
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

def calculate_equity(hero_hand, board, street, sims=3000):
    evaluator = Evaluator()
    wins, ties = 0, 0
    hero_cards = [Card.new(c) for c in hero_hand]
    board_cards = [Card.new(c) for c in board if c]
    
    current_strength = "N/A"
    if len(hero_cards) + len(board_cards) >= 5:
        current_strength = get_hand_label(evaluator.evaluate(hero_cards, board_cards[:5]))

    for _ in range(sims):
        deck = Deck()
        for c in (hero_cards + board_cards):
            if c in deck.cards: deck.cards.remove(c)
        
        opp_hand = deck.draw(2)
        
        if street == "Pre-flop": runout = deck.draw(5)
        elif street == "Flop": runout = deck.draw(2)
        elif street == "Turn": runout = deck.draw(1)
        else: runout = []
            
        full_board = board_cards + runout
        h_score = evaluator.evaluate(hero_cards, full_board)
        o_score = evaluator.evaluate(opp_hand, full_board)

        if h_score < o_score: wins += 1
        elif h_score == o_score: ties += 1
            
    return ((wins + (ties * 0.5)) / sims) * 100, current_strength

# --- UI ---
st.set_page_config(page_title="BB Poker Engine", layout="wide")
st.title("🃏 Pro Poker Decision Engine (bb)")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Hand State")
    street = st.selectbox("Street", ["Pre-flop", "Flop", "Turn", "River"])
    h1 = st.text_input("Hole Card 1", "As").capitalize()
    h2 = st.text_input("Hole Card 2", "Ks").capitalize()
    
    board_input = ""
    if street != "Pre-flop":
        board_input = st.text_input("Board (e.g., Th 7d 2s)", "").capitalize()
    board_list = board_input.split()

with col2:
    st.subheader("2. Pot Math")
    pot_bb = st.number_input("Total Pot BEFORE your call (bb)", min_value=0.0, value=10.0)
    call_bb = st.number_input("Cost to Call (bb)", min_value=0.0, value=2.0)
    
    if call_bb > 0:
        total_p = pot_bb + call_bb
        st.caption(f"💡 You are risking {call_bb}bb to win a total pot of {total_p}bb")
    
    pos = st.radio("Your Position", ["In Position", "Out of Position"])

if st.button("Calculate Best Move"):
    equity, hand_type = calculate_equity([h1, h2], board_list, street)
    
    # Break-even Equity (Pot Odds)
    be_equity = (call_bb / (pot_bb + call_bb)) * 100 if call_bb > 0 else 0
    
    st.divider()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Your Win %", f"{equity:.1f}%")
    m2.metric("Break-even %", f"{be_equity:.1f}%")
    m3.metric("Hand Strength", hand_type)

    

    # Decision Logic
    diff = equity - be_equity
    if call_bb == 0:
        st.info("## ✅ CHECK / DISCONTINUE")
    elif diff > 10:
        st.success(f"## 🔥 RAISE / VALUE BET")
        st.write(f"You have {diff:.1f}% 'Extra' equity. You are a huge favorite.")
    elif diff > 0:
        st.warning(f"## 👍 PROFITABLE CALL (+EV)")
        st.write(f"This call earns you money in the long run. You only need {be_equity:.1f}% to break even.")
    else:
        st.error(f"## ❌ FOLD (-EV)")
        st.write(f"You need {be_equity:.1f}% win rate to justify this price, but you only have {equity:.1f}%.")