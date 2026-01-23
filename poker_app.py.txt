import streamlit as st
import random
from treys import Card, Evaluator, Deck

# --- BACKEND LOGIC ---

def get_card_obj(card_str):
    """Converts a string like 'Ah' to a Treys Card object."""
    try:
        return Card.new(card_str)
    except Exception:
        return None

def generate_range(style):
    """Returns a list of hands based on opponent style."""
    ranks = "AKQJT98765432"
    suits = "shdc"
    deck = [r+s for r in ranks for s in suits]
    
    if style == "Tight (Early Pos)":
        # Premium pairs and big cards
        return [['As','Ah'], ['Ks','Kh'], ['Qs','Qh'], ['Ad','Kd'], ['Js','Jth']] # Simplified
    elif style == "Loose (Late Pos)":
        # Returns a random subset of top 40% hands (simulated for brevity)
        return [random.sample(deck, 2) for _ in range(50)] 
    else:
        # Random / Unknown
        return [random.sample(deck, 2) for _ in range(50)]

def calculate_equity(hero_hand, board, opp_style, sims=2000):
    evaluator = Evaluator()
    wins = 0
    ties = 0
    
    # Parse Hero Hand
    hero_cards = [get_card_obj(c) for c in hero_hand]
    if None in hero_cards: return 0.0

    # Parse Board
    board_cards = [get_card_obj(c) for c in board if c != ""]
    if None in board_cards: board_cards = []

    # Simulation Loop
    for _ in range(sims):
        deck = Deck()
        
        # Remove known cards from deck
        known_cards = hero_cards + board_cards
        for c in known_cards:
            if c in deck.cards:
                deck.cards.remove(c)

        # Draw Opponent Hand based on style (Simplified Random for now)
        opp_hand = deck.draw(2)
        
        # Draw remaining board
        cards_needed = 5 - len(board_cards)
        if cards_needed > 0:
            runout = deck.draw(cards_needed)
            full_board = board_cards + runout
        else:
            full_board = board_cards

        # Evaluate
        hero_score = evaluator.evaluate(hero_cards, full_board)
        opp_score = evaluator.evaluate(opp_hand, full_board)

        if hero_score < opp_score:
            wins += 1
        elif hero_score == opp_score:
            ties += 1
            
    return ((wins + (ties * 0.5)) / sims) * 100

# --- FRONTEND UI ---

st.set_page_config(page_title="Poker Decision Engine", layout="wide")

st.title("♠️ Texas Hold'em Decision Assistant")
st.markdown("Enter your hand and game state below to get a GTO-leaning recommendation.")

# Layout: Two Columns
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Your Hand & Board")
    # Input for Hero Cards
    h1 = st.text_input("Hole Card 1 (e.g., Ah)", "As").capitalize()
    h2 = st.text_input("Hole Card 2 (e.g., Kh)", "Kd").capitalize()
    
    # Input for Board
    board_input = st.text_input("Board Cards (Space separated, e.g., 'Td 7s 2c')", "").capitalize()
    board_list = board_input.split()

with col2:
    st.subheader("2. Pot Math & Context")
    pot_size = st.number_input("Current Pot Size ($)", min_value=0, value=100)
    cost_to_call = st.number_input("Cost to Call ($)", min_value=0, value=20)
    
    st.write("---")
    opp_style = st.selectbox("Opponent Style / Position", 
                             ["Unknown (Random)", "Tight (Early Pos)", "Loose (Late Pos)"])

# --- ACTION BUTTON ---

if st.button("Analyze Decision"):
    
    # 1. Calculate Pot Odds
    # Pot Odds % = Amount to Call / (Total Pot + Amount to Call)
    if cost_to_call > 0:
        total_pot_after_call = pot_size + cost_to_call
        pot_odds = (cost_to_call / total_pot_after_call) * 100
    else:
        pot_odds = 0

    # 2. Calculate Equity
    with st.spinner("Simulating 5,000 outcomes..."):
        equity = calculate_equity([h1, h2], board_list, opp_style, sims=5000)

    # 3. Render Results
    st.divider()
    st.header("Decision Report")

    # Metrics Columns
    m1, m2, m3 = st.columns(3)
    m1.metric("Your Win Probability (Equity)", f"{equity:.1f}%")
    m2.metric("Pot Odds Required", f"{pot_odds:.1f}%")
    
    diff = equity - pot_odds
    m3.metric("EV Diff", f"{diff:.1f}%", delta_color="normal")

    # 4. Final Recommendation Logic
    if cost_to_call == 0:
        st.success("## ✅ CHECK")
        st.write("It costs nothing to proceed. Never fold for free.")
    elif equity > (pot_odds + 5): # 5% buffer for safety
        st.success("## 🟢 CALL / RAISE (Profitable)")
        st.write(f"Your hand wins often enough ({equity:.1f}%) to justify the price ({pot_odds:.1f}%).")
    elif equity >= pot_odds:
        st.warning("## 🟡 MARGINAL CALL")
        st.write("This is mathematically close. Call if you think the opponent is bluffing.")
    else:
        st.error("## 🔴 FOLD")
        st.write(f"You are paying {pot_odds:.1f}% to win a hand that only wins {equity:.1f}% of the time.")