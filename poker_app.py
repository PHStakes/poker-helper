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
    if not board_strs or len(board_strs) < 3:
        return "N/A", False
    suits = [c[1] for c in board_strs]
    max_suit = max([suits.count(s) for s in set(suits)])
    ranks = sorted([Card.get_rank_int(Card.new(c)) for c in board_strs])
    is_connected = any(ranks[i+1] - ranks[i] <= 2 for i in range(len(ranks)-1))
    
    is_wet = max_suit >= 2 or is_connected
    texture_label = "Wet/Dangerous" if is_wet else "Dry/Static"
    return texture_label, is_wet

def calculate_equity(hero_hand, board_strs, street, sims=2000):
    evaluator = Evaluator()
    wins, ties = 0, 0
    try:
        hero_cards = [Card.new(c) for c in hero_hand]
        board_cards = [Card.new(c) for c in board_strs]
    except:
        return 0, "Error: Invalid Cards"

    current_strength = "N/A"
    if len(hero_cards + board_cards) >= 5:
        current_strength = get_hand_label(evaluator.evaluate(hero_cards, board_cards[:5]))

    for _ in range(sims):
        deck = Deck()
        for c in (hero_cards + board_cards):
            if c in deck.cards: deck.cards.remove(c)
        opp_hand = deck.draw(2)
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

# --- CALCULATION ---

if st.button("Get Pro Recommendation"):
    with st.spinner("Analyzing..."):
        equity, hand_type = calculate_equity([h1, h2], board_list, street)
        texture_label, is_wet = analyze_texture(board_list)
        
    st.divider()
    
    # Metrics Display
    res1, res2 = st.columns(2)
    res1.metric("Win Probability", f"{equity:.1f}%")
    res1.metric("Hand Strength", hand_type)
    
    # Texture and Bluff logic only for Post-flop
    is_bluff_candidate = False
    if street != "Pre-flop":
        res2.metric("Board Texture", texture_label)
        # Bluff conditions: Low strength but high "potential" (Equity 25-45%) on Wet boards
        if hand_type in ["High Card", "Pair"] and 25 < equity < 45 and is_wet:
            is_bluff_candidate = True
            res2.warning("⚠️ BLUFF OPPORTUNITY DETECTED")

    # --- DECISION LOGIC ---

    if action == "Facing a Bet":
        be_equity = (cost_to_call / (pot_bb + cost_to_call)) * 100
        diff = equity - be_equity
        if diff > 15:
            st.success(f"## ✅ RAISE to {cost_to_call * 3:.1f}bb")
        elif diff > 0:
            st.warning("## ✅ CALL")
        elif is_bluff_candidate and pos == "In Position (Last)":
            st.info("## 🧐 BLAZE/RAISE BLUFF")
            st.write("Aggressive Line: Your hand is weak now but has high draw potential on this wet board.")
        else:
            st.error("## ❌ FOLD")

    else: # Lead Action
        if street == "Pre-flop":
            if equity > 58: st.success("## 🟢 OPEN RAISE (2.5bb)")
            else: st.error("## ⚪ FOLD")
        else:
            if equity > 65:
                size = 0.33 if not is_wet else 0.75
                st.success(f"## 🟢 VALUE BET ({pot_bb * size:.1f}bb)")
            elif is_bluff_candidate:
                st.warning(f"## 🔵 SEMI-BLUFF BET ({pot_bb * 0.5:.1f}bb)")
                st.write("Reason: High draw potential on a wet board. Try to take the pot now.")
            elif equity > 45:
                st.info("## 🟡 CHECK (Pot Control)")
            else:
                st.error("## ⚪ CHECK / FOLD")