import streamlit as st
import random
from treys import Card, Evaluator, Deck

# --- ENGINE ---
def calculate_equity(hero_hand, board, street, sims=3000):
    evaluator = Evaluator()
    wins, ties = 0, 0
    hero_cards = [Card.new(c) for c in hero_hand]
    board_cards = [Card.new(c) for c in board if c]

    for _ in range(sims):
        deck = Deck()
        for c in (hero_cards + board_cards):
            if c in deck.cards: deck.cards.remove(c)
        
        opp_hand = deck.draw(2)
        
        # Simulation adjusts based on current street
        if street == "Pre-flop":
            runout = deck.draw(5)
        elif street == "Flop":
            runout = deck.draw(2)
        elif street == "Turn":
            runout = deck.draw(1)
        else: # River
            runout = []
            
        full_board = board_cards + runout
        h_score = evaluator.evaluate(hero_cards, full_board)
        o_score = evaluator.evaluate(opp_hand, full_board)

        if h_score < o_score: wins += 1
        elif h_score == o_score: ties += 1
            
    return ((wins + (ties * 0.5)) / sims) * 100

# --- UI ---
st.set_page_config(page_title="BB Poker Engine", layout="wide")
st.title("🃏 Pro Poker Decision Engine (bb)")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Current State")
    street = st.selectbox("Current Street", ["Pre-flop", "Flop", "Turn", "River"])
    
    h1 = st.text_input("Hole Card 1", "As").capitalize()
    h2 = st.text_input("Hole Card 2", "Ks").capitalize()
    
    board_input = ""
    if street != "Pre-flop":
        board_input = st.text_input("Board (e.g., Th 7d 2s)", "").capitalize()
    
    board_list = board_input.split()

with col2:
    st.subheader("Pot Math (in Big Blinds)")
    pot_bb = st.number_input("Total Pot (bb)", min_value=0.0, value=10.0, step=0.5)
    call_bb = st.number_input("Cost to Call (bb)", min_value=0.0, value=2.0, step=0.5)
    
    # Position logic
    pos = st.radio("Your Position", ["In Position (Last to act)", "Out of Position (First to act)"])

if st.button("Calculate Best Move"):
    equity = calculate_equity([h1, h2], board_list, street)
    
    # Pot Odds Calculation
    # Amount to call / (Total Pot including your call)
    pot_odds = (call_bb / (pot_bb + call_bb)) * 100 if call_bb > 0 else 0
    
    st.divider()
    
    # Display Results
    res1, res2 = st.columns(2)
    res1.metric("Hand Equity", f"{equity:.1f}%")
    res2.metric("Pot Odds", f"{pot_odds:.1f}%")

    # Decision Engine Logic
    # We add a 2% "Position Penalty" if Out of Position (OOP)
    threshold = pot_odds + (3.0 if pos == "Out of Position (First to act)" else 0.0)

    if call_bb == 0:
        st.info("## ACTION: CHECK / PASSIVE")
    elif equity > (threshold + 10):
        st.success("## ACTION: RAISE / VALUE BET")
        st.write("You have a significant equity advantage. Build the pot.")
    elif equity > threshold:
        st.warning("## ACTION: CALL")
        st.write(f"Mathematically profitable (+EV) call based on {pot_odds:.1f}% pot odds.")
    else:
        st.error("## ACTION: FOLD")
        st.write("The math doesn't justify the price. Fold and wait for a better spot.")