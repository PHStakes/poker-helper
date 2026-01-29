import streamlit as st
import random
from treys import Card, Evaluator, Deck

# --- UTILITY: CLEAN INPUTS ---
def clean_card_input(card_str):
    """Fixes common typos like '10s' to 'Ts'."""
    if not card_str: return ""
    card_str = card_str.strip().replace("10", "T")
    return card_str

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
    """Determines if the board is Wet or Dry."""
    if not board_strs or len(board_strs) < 3:
        return "N/A", False
    
    try:
        cards = [Card.new(clean_card_input(c)) for c in board_strs]
        suits = [Card.get_suit_int(c) for c in cards]
        max_suit_count = max([suits.count(s) for s in set(suits)])
        
        ranks = sorted([Card.get_rank_int(c) for c in cards])
        is_connected = any(ranks[i+1] - ranks[i] <= 2 for i in range(len(ranks)-1))
        
        is_wet = max_suit_count >= 2 or is_connected
        return ("Wet/Dangerous" if is_wet else "Dry/Static"), is_wet
    except:
        return "Error in Card Input", False

def calculate_equity(hero_hand, board_strs, street, sims=2000):
    evaluator = Evaluator()
    wins, ties = 0, 0
    
    try:
        hero_cards = [Card.new(clean_card_input(c)) for c in hero_hand]
        # Only process board if it exists
        board_cards = []
        if board_strs:
            board_cards = [Card.new(clean_card_input(c)) for c in board_strs]
    except Exception as e:
        return 0, f"Input Error: {e}"

    current_strength = "N/A"
    if len(hero_cards + board_cards) >= 5:
        current_strength = get_hand_label(evaluator.evaluate(hero_cards, board_cards[:5]))

    for _ in range(sims):
        deck = Deck()
        for c in (hero_cards + board_cards):
            if c in deck.cards: deck.cards.remove(c)
        
        opp_hand = deck.draw(2)
        cards_to_draw = 5 - len(board_cards)
        
        # Draw runout if needed
        if cards_to_draw > 0:
            runout = deck.draw(cards_to_draw)
            full_board = board_cards + runout
        else:
            full_board = board_cards
        
        h_score = evaluator.evaluate(hero_cards, full_board)
        opp_score = evaluator.evaluate(opp_hand, full_board)

        # FIX IS HERE: compare h_score vs opp_score (not o_score)
        if h_score < opp_score: wins += 1
        elif h_score == opp_score: ties += 1
            
    return (wins + (ties * 0.5)) / sims * 100, current_strength

# --- UI LAYOUT ---
st.set_page_config(page_title="Smart Poker Assistant", layout="wide")
st.title("🃏 Smart Poker Assistant (bb)")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Hand Input")
    street = st.selectbox("Current Street", ["Pre-flop", "Flop", "Turn", "River"])
    
    c1, c2 = st.columns(2)
    h1 = c1.text_input("Hole Card 1", "As")
    h2 = c2.text_input("Hole Card 2", "Ks")
    
    board_list = []
    if street != "Pre-flop":
        board_input = st.text_input("Board Cards (e.g., Th 7d 2s)", "")
        board_list = board_input.split()

with col2:
    st.subheader("2. Action & Pot")
    pot_bb = st.number_input("Current Pot (bb)", min_value=1.0, value=10.0)
    action = st.radio("What happened?", ["Checked to Me / First to Act", "Facing a Bet"])
    
    cost_to_call = 0.0
    if action == "Facing a Bet":
        cost_to_call = st.number_input("Cost to Call (bb)", min_value=0.1, value=5.0)
    
    pos = st.radio("Position", ["In Position (Last)", "Out of Position (First)"])

# --- RESULTS ---
if st.button("Get Pro Recommendation"):
    with st.spinner("Analyzing math..."):
        equity, hand_type = calculate_equity([h1, h2], board_list, street)
        
    st.divider()
    
    res1, res2 = st.columns(2)
    res1.metric("Win Probability", f"{equity:.1f}%")
    res1.metric("Hand Strength", hand_type)

    is_bluff_candidate = False
    
    if street != "Pre-flop":
        texture_label, is_wet = analyze_texture(board_list)
        res2.metric("Board Texture", texture_label)
        
        if hand_type in ["High Card", "Pair"] and 25 < equity < 45 and is_wet:
            is_bluff_candidate = True
            res2.warning("⚠️ BLUFF OPPORTUNITY")

    # Final Decision Output
    if action == "Facing a Bet":
        be_equity = (cost_to_call / (pot_bb + cost_to_call)) * 100
        if (equity - be_equity) > 15: st.success(f"## ✅ RAISE to {cost_to_call * 3:.1f}bb")
        elif equity > be_equity: st.warning("## ✅ CALL")
        else: st.error("## ❌ FOLD")
    else:
        if street == "Pre-flop":
            if equity > 58: st.success("## 🟢 OPEN RAISE (2.5bb)")
            else: st.error("## 🔴 FOLD")
        else:
            if equity > 65:
                texture_label, is_wet = analyze_texture(board_list)
                size = 0.75 if is_wet else 0.33
                st.success(f"## 🟢 VALUE BET ({pot_bb * size:.1f}bb)")
            elif is_bluff_candidate:
                st.warning(f"## 🔵 SEMI-BLUFF BET ({pot_bb * 0.5:.1f}bb)")
            elif equity > 45: st.info("## 🟡 CHECK (Pot Control)")
            else: st.error("## ⚪ CHECK / FOLD")
