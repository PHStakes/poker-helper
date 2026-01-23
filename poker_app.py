import streamlit as st
import random
from treys import Card, Evaluator, Deck

# --- ANALYTICS ENGINE ---

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

def analyze_texture(board_strs):
    """Automatically determines if the board is 'Wet' or 'Dry'."""
    if not board_strs or len(board_strs) < 3:
        return "Dry"
    
    # Check Suitedness
    suits = [c[1] for c in board_strs]
    max_suit = max([suits.count(s) for s in set(suits)])
    
    # Check Connectedness
    ranks = sorted([Card.get_rank_int(Card.new(c)) for c in board_strs])
    is_connected = any(ranks[i+1] - ranks[i] <= 2 for i in range(len(ranks)-1))
    
    if max_suit >= 2 or is_connected:
        return "Wet"
    return "Dry"

def calculate_equity(hero_hand, board_strs, street, sims=2000):
    evaluator = Evaluator()
    wins, ties = 0, 0
    
    try:
        hero_cards = [Card.new(c) for c in hero_hand]
        board_cards = [Card.new(c) for c in board_strs]
    except:
        return 0, "Error: Invalid Cards"

    # Current Strength (if possible)
    current_strength = "N/A"
    if len(hero_cards + board_cards) >= 5:
        current_strength = get_hand_label(evaluator.evaluate(hero_cards, board_cards[:5]))

    for _ in range(sims):
        deck = Deck()
        for c in (hero_cards + board_cards):
            if c in deck.cards: deck.cards.remove(c)
        
        opp_hand = deck.draw(2)
        
        # Complete the board based on the street
        cards_to_draw = 5 - len(board_cards)
        full_board = board_cards + (deck.draw(cards_to_draw) if cards_to_draw > 0 else [])
        
        h_score = evaluator.evaluate(hero_cards, full_board)
        o_score = evaluator.evaluate(opp_hand, full_board)

        if h_score < o_score: wins += 1
        elif h_score == o_score: ties += 1
            
    return (wins + (ties * 0.5)) / sims * 100, current_strength

# --- UI LAYOUT ---

st.set_page_config(page_title="GTO Decision Engine", layout="wide")
st.title("🃏 Smart Poker Assistant (bb)")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Hand Input")
    street = st.selectbox("Current Street", ["Pre-flop", "Flop", "Turn", "River"])
    
    c1, c2 = st.columns(2)
    h1 = c1.text_input("Hole Card 1", "As").capitalize()
    h2 = c2.text_input("Hole Card 2", "Ks").capitalize()
    
    board_list = []
    if street != "Pre-flop":
        board_input = st.text_input("Board Cards (e.g., Th 7d 2s)", "").capitalize()
        board_list = board_input.split()

with col2:
    st.subheader("2. Action & Pot")
    pot_bb = st.number_input("Current Pot (bb)", min_value=1.0, value=10.0)
    action = st.radio("What happened?", ["Checked to Me / First to Act", "Facing a Bet"])
    
    cost_to_call = 0.0
    if action == "Facing a Bet":
        cost_to_call = st.number_input("Cost to Call (bb)", min_value=0.1, value=5.0)

    pos = st.radio("Position", ["In Position (Last)", "Out of Position (First)"])

# --- CALCULATION & DECISION ---

if st.button("Get Pro Recommendation"):
    with st.spinner("Analyzing..."):
        equity, hand_type = calculate_equity([h1, h2], board_list, street)
        texture = analyze_texture(board_list)
        
    st.divider()
    
    # 1. Metrics Display
    res1, res2, res3 = st.columns(3)
    res1.metric("Win Probability", f"{equity:.1f}%")
    res2.metric("Hand Strength", hand_type)
    res3.metric("Board Texture", texture)

    # 2. Decision Logic
    if action == "Facing a Bet":
        # DEFENSIVE LOGIC
        be_equity = (cost_to_call / (pot_bb + cost_to_call)) * 100
        diff = equity - be_equity
        
        st.write(f"**Break-even Equity required:** {be_equity:.1f}%")
        
        if diff > 15:
            st.success(f"## ✅ RAISE")
            st.write(f"**Suggested Size:** {cost_to_call * 3:.1f}bb (3x their bet)")
        elif diff > 0:
            st.warning("## ✅ CALL")
            st.write("You have the math to continue, but not enough to raise.")
        else:
            st.error("## ❌ FOLD")
            st.write("You are not winning often enough to justify this price.")

    else:
        # OFFENSIVE LOGIC (Checked to user or First to act)
        if street == "Pre-flop":
            if equity > 58:
                st.success("## 🟢 RAISE (Open)")
                st.write("**Size:** 2.5bb - 3.0bb")
            else:
                st.error("## ⚪ FOLD")
        
        else:
            if equity > 65:
                st.success("## 🟢 VALUE BET")
                # Sizing based on texture
                size = 0.33 if texture == "Dry" else 0.75
                st.write(f"**Size:** {pot_bb * size:.1f}bb ({int(size*100)}% Pot)")
                st.write(f"Reasoning: {texture} boards require {'smaller sizes to keep them in' if texture == 'Dry' else 'larger sizes to protect your hand'}.")
            elif equity > 45:
                st.info("## 🟡 CHECK")
                st.write("Medium strength hand. Take a free card and control the pot.")
            else:
                st.error("## ⚪ CHECK / FOLD")