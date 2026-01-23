import streamlit as st
import random
from treys import Card, Evaluator, Deck

# --- ENGINE ---
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

def calculate_equity(hero_hand, board, street, sims=2000):
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
    
    board_texture = st.selectbox("Board Texture", ["Dry (Unconnected)", "Wet (Many Draws)", "Paired/Monotone"])

with col2:
    st.subheader("2. Action & Pot")
    pot_bb = st.number_input("Total Pot (bb)", min_value=0.0, value=10.0)
    action_type = st.radio("Action is...", ["Facing a Bet/Raise", "Checked to Me / I am First"])
    
    call_bb = 0.0
    if action_type == "Facing a Bet/Raise":
        call_bb = st.number_input("Cost to Call (bb)", min_value=0.1, value=5.0)
    
    pos = st.radio("Position", ["In Position", "Out of Position"])

if st.button("Calculate Best Move"):
    equity, hand_type = calculate_equity([h1, h2], board_list, street)
    st.divider()
    
    # Logic for DEFENSIVE (Facing a bet)
    if action_type == "Facing a Bet/Raise":
        be_equity = (call_bb / (pot_bb + call_bb)) * 100
        st.metric("Win %", f"{equity:.1f}%", f"Need >{be_equity:.1f}%")
        
        if equity > (be_equity + 15):
            st.success("## 🔥 RAISE")
            st.write(f"Sizing: 3x their bet ({call_bb * 3}bb)")
        elif equity > be_equity:
            st.warning("## 👍 CALL")
        else:
            st.error("## ❌ FOLD")

    # Logic for OFFENSIVE (Checked to user / First to act)
    else:
        st.metric("Win %", f"{equity:.1f}%")
        
        if street == "Pre-flop":
            if equity > 55:
                st.success("## 🟢 OPEN RAISE")
                st.write("Sizing: 2.5bb - 3.5bb")
            else:
                st.error("## 🔴 FOLD / LIMP")
        
        else: # Post-flop lead
            if equity > 65:
                st.success("## 🟢 VALUE BET")
                # Sizing logic based on texture
                if board_texture == "Dry (Unconnected)":
                    st.write(f"Sizing: 33% Pot ({pot_bb * 0.33:.1f}bb)")
                else:
                    st.write(f"Sizing: 75% Pot ({pot_bb * 0.75:.1f}bb)")
            elif equity > 45:
                st.info("## ✅ CHECK (Pot Control)")
                st.write("Your hand is strong but vulnerable. Keep the pot small.")
            else:
                st.error("## ⚪ CHECK / FOLD")
                st.write("Do not bluff unless you have a strong draw (4+ outs).")